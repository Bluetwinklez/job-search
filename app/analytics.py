"""Başvuru analitiği, dönüşüm hunisi ve istatistik motoru."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict


def get_funnel_metrics(db_path: Path) -> Dict[str, Any]:
    """Başvuru dönüşüm hunisi (funnel) metriklerini hesaplar."""
    if not db_path.exists():
        return {
            "total": 0,
            "applied": 0,
            "interview": 0,
            "offer": 0,
            "rejected": 0,
            "applied_rate": 0.0,
            "interview_rate": 0.0,
            "offer_rate": 0.0,
        }

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
    counts = dict(cur.fetchall())
    conn.close()

    total = sum(counts.values())
    applied = counts.get("başvuruldu", 0) + counts.get("mülakat", 0) + counts.get("teklif", 0) + counts.get("reddedildi", 0)
    interview = counts.get("mülakat", 0) + counts.get("teklif", 0)
    offer = counts.get("teklif", 0)
    rejected = counts.get("reddedildi", 0)

    applied_rate = round((applied / total * 100), 1) if total > 0 else 0.0
    interview_rate = round((interview / applied * 100), 1) if applied > 0 else 0.0
    offer_rate = round((offer / interview * 100), 1) if interview > 0 else 0.0

    return {
        "total": total,
        "applied": applied,
        "interview": interview,
        "offer": offer,
        "rejected": rejected,
        "applied_rate": applied_rate,
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
    }


def get_platform_distribution(db_path: Path) -> Dict[str, int]:
    """İlanların platformlara (LinkedIn, Indeed, vb.) göre dağılımını döner."""
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT site, COUNT(*) FROM jobs WHERE site IS NOT NULL AND site != '' GROUP BY site")
    res = dict(cur.fetchall())
    conn.close()
    return res


def get_score_distribution(db_path: Path) -> Dict[str, int]:
    """Eşleşme skorlarının aralıklara göre dağılımını döner."""
    res = {
        "🎯 %80 - %100 (Yüksek)": 0,
        "⚡ %60 - %79 (Orta)": 0,
        "🔍 %40 - %59 (Düşük)": 0,
        "⚪ %0 - %39 / Skorsuz": 0,
    }
    if not db_path.exists():
        return res

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT match_score FROM jobs")
    rows = cur.fetchall()
    conn.close()

    for (score,) in rows:
        if score is None:
            res["⚪ %0 - %39 / Skorsuz"] += 1
        elif score >= 0.80:
            res["🎯 %80 - %100 (Yüksek)"] += 1
        elif score >= 0.60:
            res["⚡ %60 - %79 (Orta)"] += 1
        elif score >= 0.40:
            res["🔍 %40 - %59 (Düşük)"] += 1
        else:
            res["⚪ %0 - %39 / Skorsuz"] += 1

    return res
