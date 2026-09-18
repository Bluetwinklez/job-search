import tempfile
import unittest
from pathlib import Path
import sqlite3

from app.analytics import (
    get_funnel_metrics,
    get_platform_distribution,
    get_score_distribution,
    get_status_distribution,
)


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_analytics.db"

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE jobs (
                job_url TEXT PRIMARY KEY,
                site TEXT,
                title TEXT,
                status TEXT,
                match_score REAL
            )
            """
        )
        conn.executemany(
            "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
            [
                ("u1", "linkedin", "Dev 1", "yeni", 0.85),
                ("u2", "linkedin", "Dev 2", "başvuruldu", 0.70),
                ("u3", "indeed", "Dev 3", "mülakat", 0.90),
                ("u4", "indeed", "Dev 4", "teklif", 0.95),
                ("u5", "glassdoor", "Dev 5", "reddedildi", 0.45),
                ("u6", "google", "Dev 6", "yeni", None),
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_funnel_metrics(self):
        m = get_funnel_metrics(self.db_path)
        self.assertEqual(m["total"], 6)
        # Başvurulan = başvuruldu(1) + mülakat(1) + teklif(1) + reddedildi(1) = 4
        self.assertEqual(m["applied"], 4)
        # Mülakat = mülakat(1) + teklif(1) = 2
        self.assertEqual(m["interview"], 2)
        # Teklif = 1
        self.assertEqual(m["offer"], 1)

        self.assertAlmostEqual(m["applied_rate"], 66.7, places=1)
        self.assertAlmostEqual(m["interview_rate"], 50.0, places=1)
        self.assertAlmostEqual(m["offer_rate"], 50.0, places=1)

    def test_platform_distribution(self):
        dist = get_platform_distribution(self.db_path)
        self.assertEqual(dist["linkedin"], 2)
        self.assertEqual(dist["indeed"], 2)
        self.assertEqual(dist["glassdoor"], 1)
        self.assertEqual(dist["google"], 1)

    def test_score_distribution(self):
        dist = get_score_distribution(self.db_path)
        self.assertEqual(dist["🎯 %80 - %100 (Yüksek)"], 3)  # 0.85, 0.90, 0.95
        self.assertEqual(dist["⚡ %60 - %79 (Orta)"], 1)  # 0.70
        self.assertEqual(dist["🔍 %40 - %59 (Düşük)"], 1)  # 0.45
        self.assertEqual(dist["⚪ %0 - %39 / Skorsuz"], 1)  # None


    def test_status_distribution(self):
        dist = get_status_distribution(self.db_path)
        self.assertEqual(dist["yeni"], 2)
        self.assertEqual(dist["başvuruldu"], 1)
        self.assertEqual(dist["mülakat"], 1)
        self.assertEqual(dist["teklif"], 1)
        self.assertEqual(dist["reddedildi"], 1)


if __name__ == "__main__":
    unittest.main()
