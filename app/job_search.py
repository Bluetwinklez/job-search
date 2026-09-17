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

from app.matching import contains_keyword
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
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA)
    existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
    if "status" not in existing_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'yeni'")
    if "notes" not in existing_cols:
        conn.execute("ALTER TABLE jobs ADD COLUMN notes TEXT")


def _profile_keywords(profile: Profile) -> set[str]:
    keywords: set[str] = set()
    for group in profile.skills:
        keywords.update(item.strip().lower() for item in group.items)
    for exp in profile.experience:
        keywords.update(t.strip().lower() for t in exp.tech_stack)
    return {k for k in keywords if k}


def _match_score(description: str | None, keywords: set[str]) -> float | None:
    if not isinstance(description, str) or not description or not keywords:
        return None
    hits = sum(1 for kw in keywords if contains_keyword(description, kw))
    return round(hits / len(keywords), 3)


def search_jobs(
    search_term: str,
    location: str | None,
    sites: list[str],
    results_wanted: int,
    hours_old: int | None = None,
    country_indeed: str = "turkey",
    linkedin_fetch_description: bool = False,
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
        description = _clean(row.get("description"))
        score = _match_score(description, keywords) if keywords else None
        cur = conn.execute(
            """
            INSERT INTO jobs (job_url, site, title, company, location, job_type,
                               date_posted, description, match_score, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET match_score = excluded.match_score
            """,
            (
                job_url,
                _clean(row.get("site")) or "",
                _clean(row.get("title")),
                _clean(row.get("company")),
                _clean(row.get("location")) or "",
                _clean(row.get("job_type")) or "",
                _clean(row.get("date_posted")) or "",
                description,
                score,
                fetched_at,
            ),
        )
        if cur.rowcount:
            new_count += 1
    conn.commit()
    conn.close()
    return new_count


def list_jobs(
    db_path: Path,
    limit: int = 20,
    min_score: float | None = None,
    status: str | None = None,
):
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    query = (
        "SELECT job_url, site, title, company, location, job_type, date_posted, "
        "match_score, status, notes, fetched_at FROM jobs"
    )
    clauses = []
    params: list = []
    if min_score is not None:
        clauses.append("match_score >= ?")
        params.append(min_score)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY fetched_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


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
    )
    for site, error in errors:
        print(f"Uyarı: {site} taranamadı ({error})")

    if df is None or df.empty:
        print("Sonuç bulunamadı.")
        return

    new_count = save_jobs(df, args.db, profile)
    print(f"{len(df)} ilan tarandı, {new_count} yeni ilan '{args.db}' içine kaydedildi.")


if __name__ == "__main__":
    main()
