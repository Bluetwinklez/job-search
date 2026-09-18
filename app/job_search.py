"""Çoklu platformdan iş ilanı tarama.

Taramayı `jobspy` (python-jobspy) kütüphanesi üzerinden yapar; bu kütüphane
LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter, Bayt ve Naukri'yi tek bir
arayüzden destekler. Sonuçlar tekilleştirilerek yerel bir SQLite veritabanında
saklanır; profil verildiğinde her ilan için basit bir yetenek eşleşme skoru
hesaplanır.

Kullanım:
    python -m app.job_search --search-term "Backend Developer" \\
        --location "Istanbul, Turkey" --results 20 --profile data/profile.json

Not: Buradaki taramalar ilgili sitelerin herkese açık arama sonuçlarını
kullanır. Sık/aşırı istek atmak ilgili sitenin kullanım koşullarını ihlal
edebilir ve IP engellemesine yol açabilir; `--results` değerini makul tut.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

from app.matching import contains_keyword, extract_matching_keywords, split_keywords, turkish_lower
from app.models import Profile

ALL_SITES = [
    "linkedin",
    "indeed",
    "glassdoor",
    "google",
    "zip_recruiter",
    "bayt",
    "naukri",
]

DEFAULT_DB_PATH = Path("data/jobs.db")

STATUSES = ["yeni", "başvuruldu", "mülakat", "reddedildi", "teklif"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_url TEXT PRIMARY KEY,
    site TEXT,
    title TEXT,
    company TEXT,
    location TEXT,
    job_type TEXT,
    date_posted TEXT,
    description TEXT,
    match_score REAL,
    fetched_at TEXT,
    status TEXT NOT NULL DEFAULT 'yeni',
    notes TEXT
);

CREATE TABLE IF NOT EXISTS saved_searches (
    name TEXT PRIMARY KEY,
    search_term TEXT,
    location TEXT,
    sites TEXT,
    is_remote INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT,
    location TEXT,
    sites TEXT,
    result_count INTEGER,
    searched_at TEXT
);

CREATE TABLE IF NOT EXISTS company_watchlist (
    company TEXT PRIMARY KEY,
    search_term TEXT,
    added_at TEXT
);

CREATE TABLE IF NOT EXISTS blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE NOT NULL,
    kind TEXT NOT NULL DEFAULT 'company',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS interview_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_url TEXT,
    category TEXT,
    question TEXT NOT NULL,
    rationale TEXT,
    answer_tip TEXT,
    personal_answer TEXT,
    created_at TEXT NOT NULL
);
"""

_JOBS_EXTRA_COLUMNS = {
    "favorite": "INTEGER NOT NULL DEFAULT 0",
    "min_amount": "REAL",
    "max_amount": "REAL",
    "currency": "TEXT",
    "salary_interval": "TEXT",
    "is_remote": "INTEGER",
}


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "status" not in existing_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'yeni'")
    if "notes" not in existing_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN notes TEXT")
    for col, col_type in _JOBS_EXTRA_COLUMNS.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")


def _profile_keywords(profile: Profile) -> set[str]:
    """Profildeki yetenek/teknoloji ifadelerinden eşleşme anahtar kelimelerini çıkarır.

    Hem ifadenin tamamını (ör. "reçete karşılama") hem de anlamlı tekil
    kelimelerini (ör. "reçete", "karşılama") ekler (Türkçe karakter uyumlu).
    """
    items: list[str] = []
    for group in profile.skills:
        items.extend(group.items)
    for exp in profile.experience:
        items.extend(exp.tech_stack)

    keywords: set[str] = set()
    for item in items:
        item = item.strip()
        if not item:
            continue
        keywords.add(turkish_lower(item))
        keywords.update(split_keywords(item))
    return keywords


def _match_score(text: str | None, keywords: set[str]) -> float | None:
    if not isinstance(text, str) or not text.strip() or not keywords:
        return None
    hits = sum(1 for kw in keywords if contains_keyword(text, kw))
    if hits == 0:
        return 0.0
    # Tipik bir ilan 4-10 arası yetenek arar; çok geniş profile sahip adayların
    # skoru gereksiz yere cezalandırılmasın diye min(len(keywords), 10) ile normalize edilir.
    effective_total = min(len(keywords), 10)
    return round(min(1.0, hits / effective_total), 3)


def get_matched_skills(text: str | None, profile: Profile | None) -> list[str]:
    """İlan metni ile eşleşen profil yeteneklerini döner."""
    if not text or not profile:
        return []
    keywords = _profile_keywords(profile)
    return extract_matching_keywords(text, keywords)



def search_jobs(
    search_term: str,
    location: str | None,
    sites: list[str],
    results_wanted: int,
    hours_old: int | None = None,
    country_indeed: str = "turkey",
    linkedin_fetch_description: bool = False,
    is_remote: bool = False,
):
    """Verilen platformları paralel ve birbirinden izole şekilde tarar.

    JobSpy'ın kendi toplu (`scrape_jobs(site_name=[...])`) çağrısı, bir
    platform/ülke kombinasyonu desteklenmediğinde (ör. Glassdoor'un
    olmadığı bir ülke) tüm taramayı istisna fırlatarak durdurur ve o ana
    kadar başarıyla çekilmiş diğer platformların sonuçlarını da kaybeder.
    Bunu önlemek için her platform ayrı bir `scrape_jobs` çağrısıyla,
    kendi thread havuzumuzda paralel olarak taranır: bir platform hata
    verirse yalnızca o platform atlanır, diğerleri yeniden istek atılmadan
    korunur. Başarısız platformlar (site, hata mesajı) listesi olarak
    döndürülür.
    """

    def _scrape_one(site: str):
        return scrape_jobs(
            site_name=[site],
            search_term=search_term,
            google_search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            description_format="markdown",
            country_indeed=country_indeed,
            linkedin_fetch_description=linkedin_fetch_description,
            is_remote=is_remote,
        )

    frames = []
    errors: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(len(sites), 1)) as executor:
        future_to_site = {executor.submit(_scrape_one, site): site for site in sites}
        for future in as_completed(future_to_site):
            site = future_to_site[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    frames.append(df)
            except Exception as e:
                errors.append((site, str(e)))

    if not frames:
        return pd.DataFrame(), errors
    return pd.concat(frames, ignore_index=True), errors


def _clean(value) -> str | None:
    if not isinstance(value, str):
        return None
    return value


def save_jobs(df, db_path: Path, profile: Profile | None = None) -> int:
    keywords = _profile_keywords(profile) if profile else set()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)

    new_count = 0
    fetched_at = datetime.now(timezone.utc).isoformat()
    for row in df.to_dict(orient="records"):
        job_url = row.get("job_url")
        if not job_url:
            continue
        title = _clean(row.get("title"))
        company = _clean(row.get("company"))
        location = _clean(row.get("location")) or ""
        job_type = _clean(row.get("job_type")) or ""
        date_posted = _clean(row.get("date_posted")) or ""
        description = _clean(row.get("description"))

        search_text = f"{title or ''}\n{description or ''}".strip()
        score = _match_score(search_text, keywords) if keywords else None

        min_amount = row.get("min_amount")
        max_amount = row.get("max_amount")
        currency = _clean(row.get("currency"))
        salary_interval = _clean(row.get("interval"))
        is_remote = row.get("is_remote")
        is_remote = int(bool(is_remote)) if is_remote is not None and not pd.isna(is_remote) else None

        # Gerçekten yeni mi kontrol et (SQLite rowcount yanılgısını önlemek için)
        exists = conn.execute("SELECT 1 FROM jobs WHERE job_url = ?", (job_url,)).fetchone()
        if not exists:
            new_count += 1

        conn.execute(
            """
            INSERT INTO jobs (job_url, site, title, company, location, job_type,
                               date_posted, description, match_score, fetched_at,
                               min_amount, max_amount, currency, salary_interval, is_remote)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                match_score = COALESCE(excluded.match_score, jobs.match_score),
                description = CASE WHEN excluded.description IS NOT NULL AND excluded.description != ''
                                   THEN excluded.description ELSE jobs.description END,
                location = CASE WHEN excluded.location IS NOT NULL AND excluded.location != ''
                                THEN excluded.location ELSE jobs.location END,
                date_posted = CASE WHEN excluded.date_posted IS NOT NULL AND excluded.date_posted != ''
                                   THEN excluded.date_posted ELSE jobs.date_posted END,
                job_type = CASE WHEN excluded.job_type IS NOT NULL AND excluded.job_type != ''
                                THEN excluded.job_type ELSE jobs.job_type END,
                min_amount = COALESCE(excluded.min_amount, jobs.min_amount),
                max_amount = COALESCE(excluded.max_amount, jobs.max_amount),
                currency = COALESCE(excluded.currency, jobs.currency),
                salary_interval = COALESCE(excluded.salary_interval, jobs.salary_interval),
                is_remote = COALESCE(excluded.is_remote, jobs.is_remote),
                fetched_at = excluded.fetched_at
            """,
            (
                job_url,
                _clean(row.get("site")) or "",
                title,
                company,
                location,
                job_type,
                date_posted,
                description,
                score,
                fetched_at,
                min_amount,
                max_amount,
                currency,
                salary_interval,
                is_remote,
            ),
        )
    conn.commit()
    conn.close()
    return new_count



def add_to_blacklist(db_path: Path, keyword: str, kind: str = "company") -> bool:
    """Şirket veya anahtar kelimeyi kara listeye ekler."""
    keyword = keyword.strip()
    if not keyword:
        return False
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    created_at = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            "INSERT INTO blacklist (keyword, kind, created_at) VALUES (?, ?, ?)",
            (keyword, kind, created_at),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_from_blacklist(db_path: Path, keyword: str) -> bool:
    """Kara listeden bir öğeyi kaldırır."""
    if not db_path.exists():
        return False
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute("DELETE FROM blacklist WHERE LOWER(keyword) = LOWER(?) OR keyword = ?", (keyword, keyword))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def get_blacklist(db_path: Path) -> list[dict]:
    """Kara listedeki tüm kayıtları döner."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    rows = conn.execute("SELECT id, keyword, kind, created_at FROM blacklist ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_blacklisted(company: str | None, title: str | None, blacklist_items: list[dict]) -> bool:
    """Şirketin veya ilanın kara listede olup olmadığını denetler."""
    if not blacklist_items:
        return False
    comp_lower = turkish_lower(company or "")
    title_lower = turkish_lower(title or "")
    for item in blacklist_items:
        target = turkish_lower(item.get("keyword", ""))
        if not target:
            continue
        kind = item.get("kind", "company")
        if kind == "company":
            if target in comp_lower:
                return True
        else:
            if target in title_lower or target in comp_lower:
                return True
    return False


def list_jobs(
    db_path: Path,
    limit: int = 20,
    min_score: float | None = None,
    status: str | None = None,
    favorite_only: bool = False,
    remote_only: bool = False,
    filter_blacklisted: bool = True,
):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    query = (
        "SELECT job_url, site, title, company, location, job_type, date_posted, "
        "match_score, status, notes, fetched_at, favorite, min_amount, max_amount, "
        "currency, salary_interval, is_remote, description FROM jobs"
    )
    clauses = []
    params: list = []
    if min_score is not None:
        clauses.append("match_score >= ?")
        params.append(min_score)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if favorite_only:
        clauses.append("favorite = 1")
    if remote_only:
        clauses.append("is_remote = 1")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY fetched_at DESC"

    fetch_limit = max(limit * 5, 100) if filter_blacklisted else limit
    query += f" LIMIT {fetch_limit}"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    blacklist_items = get_blacklist(db_path) if filter_blacklisted else []
    if not blacklist_items:
        return rows[:limit]

    filtered = [r for r in rows if not is_blacklisted(r["company"], r["title"], blacklist_items)]
    return filtered[:limit]


def get_job(db_path: Path, job_url: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    row = conn.execute("SELECT * FROM jobs WHERE job_url = ?", (job_url,)).fetchone()
    conn.close()
    return row


def set_status(db_path: Path, job_url: str, status: str, notes: str | None = None) -> bool:
    if status not in STATUSES:
        raise ValueError(f"Geçersiz durum: {status!r}. Geçerli değerler: {', '.join(STATUSES)}")
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    if notes is None:
        cur = conn.execute("UPDATE jobs SET status = ? WHERE job_url = ?", (status, job_url))
    else:
        cur = conn.execute(
            "UPDATE jobs SET status = ?, notes = ? WHERE job_url = ?", (status, notes, job_url)
        )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def toggle_favorite(db_path: Path, job_url: str, favorite: bool) -> bool:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute("UPDATE jobs SET favorite = ? WHERE job_url = ?", (int(favorite), job_url))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


# ------------------------------------------------------------- Kayıtlı aramalar -
def save_search(db_path: Path, name: str, search_term: str, location: str | None, sites: list[str], is_remote: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    conn.execute(
        """
        INSERT INTO saved_searches (name, search_term, location, sites, is_remote, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            search_term = excluded.search_term, location = excluded.location,
            sites = excluded.sites, is_remote = excluded.is_remote
        """,
        (name, search_term, location or "", ",".join(sites), int(is_remote), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def list_saved_searches(db_path: Path):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    rows = conn.execute("SELECT * FROM saved_searches ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def delete_saved_search(db_path: Path, name: str) -> bool:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute("DELETE FROM saved_searches WHERE name = ?", (name,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# --------------------------------------------------------------- Arama geçmişi -
def log_search(db_path: Path, search_term: str, location: str | None, sites: list[str], result_count: int) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    conn.execute(
        "INSERT INTO search_log (search_term, location, sites, result_count, searched_at) VALUES (?, ?, ?, ?, ?)",
        (search_term, location or "", ",".join(sites), result_count, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def list_search_history(db_path: Path, limit: int = 30):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM search_log ORDER BY searched_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return rows


# --------------------------------------------------------------- Şirket takibi -
def add_watched_company(db_path: Path, company: str, search_term: str) -> None:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    conn.execute(
        """
        INSERT INTO company_watchlist (company, search_term, added_at) VALUES (?, ?, ?)
        ON CONFLICT(company) DO UPDATE SET search_term = excluded.search_term
        """,
        (company, search_term, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def remove_watched_company(db_path: Path, company: str) -> bool:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute("DELETE FROM company_watchlist WHERE company = ?", (company,))
    conn.commit()
    removed = cur.rowcount > 0
    conn.close()
    return removed


def list_watched_companies(db_path: Path):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    rows = conn.execute("SELECT * FROM company_watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return rows


# ------------------------------------------------------- Mülakat soru bankası -
def save_interview_questions(db_path: Path, job_url: str | None, questions: list[dict]) -> None:
    """Üretilen mülakat sorularını (kategori/soru/gerekçe/cevap ipucu) soru bankasına kaydeder."""
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        """
        INSERT INTO interview_questions (job_url, category, question, rationale, answer_tip, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (job_url, q.get("category"), q.get("question"), q.get("rationale"), q.get("answer_tip"), now)
            for q in questions
        ],
    )
    conn.commit()
    conn.close()


def list_interview_questions(db_path: Path, job_url: str | None = None):
    """job_url verilirse yalnızca o ilana ait soruları, verilmezse tüm soru bankasını döner."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    if job_url:
        rows = conn.execute(
            "SELECT * FROM interview_questions WHERE job_url = ? ORDER BY created_at DESC", (job_url,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM interview_questions ORDER BY created_at DESC").fetchall()
    conn.close()
    return rows


def update_interview_answer(db_path: Path, question_id: int, personal_answer: str) -> bool:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute(
        "UPDATE interview_questions SET personal_answer = ? WHERE id = ?", (personal_answer, question_id)
    )
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_interview_question(db_path: Path, question_id: int) -> bool:
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    cur = conn.execute("DELETE FROM interview_questions WHERE id = ?", (question_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def get_stats(db_path: Path) -> dict:
    if not db_path.exists():
        return {"total": 0, "by_status": {s: 0 for s in STATUSES}}
    conn = sqlite3.connect(db_path)
    _ensure_schema(conn)
    rows = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
    conn.close()
    by_status = {s: 0 for s in STATUSES}
    for status, count in rows:
        by_status[status] = count
    return {"total": sum(by_status.values()), "by_status": by_status}


def main() -> None:
    parser = argparse.ArgumentParser(description="Çoklu platformdan iş ilanı tarar ve yerel veritabanına kaydeder.")
    parser.add_argument("--search-term", required=True, help="Aranacak pozisyon/anahtar kelime")
    parser.add_argument("--location", default=None, help="Konum (ör. 'Istanbul, Turkey')")
    parser.add_argument(
        "--sites",
        default=",".join(ALL_SITES),
        help=f"Virgülle ayrılmış platform listesi (varsayılan hepsi: {', '.join(ALL_SITES)})",
    )
    parser.add_argument("--results", type=int, default=15, help="Platform başına istenen sonuç sayısı")
    parser.add_argument("--hours-old", type=int, default=None, help="Yalnızca son X saat içindeki ilanlar")
    parser.add_argument("--country-indeed", default="turkey", help="Indeed için ülke (ör. turkey, usa, germany)")
    parser.add_argument(
        "--linkedin-descriptions",
        action="store_true",
        help="LinkedIn ilanları için açıklama metnini de çek (eşleşme skoru için gerekir, daha yavaştır)",
    )
    parser.add_argument("--profile", type=Path, default=None, help="Eşleşme skoru için profil JSON dosyası")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite veritabanı yolu")
    parser.add_argument("--remote", action="store_true", help="Yalnızca uzaktan çalışma ilanları")
    args = parser.parse_args()

    sites = [s.strip() for s in args.sites.split(",") if s.strip()]
    profile = None
    if args.profile:
        profile = Profile.model_validate(json.loads(args.profile.read_text(encoding="utf-8")))

    df, errors = search_jobs(
        args.search_term,
        args.location,
        sites,
        args.results,
        args.hours_old,
        args.country_indeed,
        args.linkedin_descriptions,
        args.remote,
    )
    for site, error in errors:
        print(f"Uyarı: {site} taranamadı ({error})")

    if df is None or df.empty:
        print("Sonuç bulunamadı.")
        log_search(args.db, args.search_term, args.location, sites, 0)
        return

    new_count = save_jobs(df, args.db, profile)
    log_search(args.db, args.search_term, args.location, sites, len(df))
    print(f"{len(df)} ilan tarandı, {new_count} yeni ilan '{args.db}' içine kaydedildi.")


if __name__ == "__main__":
    main()
