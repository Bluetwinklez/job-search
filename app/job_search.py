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
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jobspy import scrape_jobs

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
    fetched_at TEXT
);
"""


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
    text = description.lower()
    hits = sum(1 for kw in keywords if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", text))
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
    return scrape_jobs(
        site_name=sites,
        search_term=search_term,
        google_search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=hours_old,
        description_format="markdown",
        country_indeed=country_indeed,
        linkedin_fetch_description=linkedin_fetch_description,
    )


def _clean(value) -> str | None:
    if not isinstance(value, str):
        return None
    return value


def save_jobs(df, db_path: Path, profile: Profile | None = None) -> int:
    keywords = _profile_keywords(profile) if profile else set()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)

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


def list_jobs(db_path: Path, limit: int = 20, min_score: float | None = None):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    query = "SELECT job_url, site, title, company, location, match_score, fetched_at FROM jobs"
    params: list = []
    if min_score is not None:
        query += " WHERE match_score >= ?"
        params.append(min_score)
    query += " ORDER BY fetched_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


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

    df = search_jobs(
        args.search_term,
        args.location,
        sites,
        args.results,
        args.hours_old,
        args.country_indeed,
        args.linkedin_descriptions,
    )
    if df is None or df.empty:
        print("Sonuç bulunamadı.")
        return

    new_count = save_jobs(df, args.db, profile)
    print(f"{len(df)} ilan tarandı, {new_count} yeni ilan '{args.db}' içine kaydedildi.")


if __name__ == "__main__":
    main()
