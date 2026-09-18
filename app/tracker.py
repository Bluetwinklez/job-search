"""Başvuru takibi: taranan ilanların durumunu yönetir.

Kullanım (--db verilmezse varsayılan olarak data/jobs.db kullanılır, alt
komuttan önce gelmelidir):
    python -m app.tracker list --status başvuruldu
    python -m app.tracker --db data/jobs.db set "<job_url>" mülakat --notes "Teknik mülakat 25 Eylül"
    python -m app.tracker stats
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.job_search import DEFAULT_DB_PATH, STATUSES, get_stats, list_jobs, set_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Başvuru durumu takibi")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite veritabanı yolu")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Kayıtlı ilanları listele")
    p_list.add_argument("--status", choices=STATUSES, default=None)
    p_list.add_argument("--limit", type=int, default=30)

    p_set = sub.add_parser("set", help="Bir ilanın durumunu güncelle")
    p_set.add_argument("job_url")
    p_set.add_argument("status", choices=STATUSES)
    p_set.add_argument("--notes", default=None)

    sub.add_parser("stats", help="Durum bazlı özet istatistik göster")

    args = parser.parse_args()

    if args.command == "list":
        rows = list_jobs(args.db, limit=args.limit, status=args.status)
        if not rows:
            print("Kayıt bulunamadı.")
            return
        for row in rows:
            score = f"{row['match_score']:.0%}" if row["match_score"] is not None else "-"
            print(f"[{row['status']:<10}] {score:>5}  {row['title']} — {row['company']} ({row['site']})")
            print(f"    {row['job_url']}")

    elif args.command == "set":
        updated = set_status(args.db, args.job_url, args.status, args.notes)
        print("Güncellendi." if updated else "İlan bulunamadı.")

    elif args.command == "stats":
        stats = get_stats(args.db)
        print(f"Toplam: {stats['total']}")
        for status, count in stats["by_status"].items():
            print(f"  {status}: {count}")
        applied = sum(stats["by_status"][s] for s in ("başvuruldu", "mülakat", "reddedildi", "teklif"))
        responded = sum(stats["by_status"][s] for s in ("mülakat", "reddedildi", "teklif"))
        if applied:
            print(f"Geri dönüş oranı: {responded / applied:.0%} ({responded}/{applied})")


if __name__ == "__main__":
    main()
