import tempfile
import unittest
from pathlib import Path

try:
    import pandas as pd
    def create_df(records):
        return pd.DataFrame(records)
except ImportError:
    class MockDataFrame:
        def __init__(self, records):
            self.records = records
        def to_dict(self, orient="records"):
            return self.records
    def create_df(records):
        return MockDataFrame(records)


from app.job_search import (
    _match_score,
    add_watched_company,
    delete_saved_search,
    get_job,
    get_matched_skills,
    get_stats,
    list_jobs,
    list_saved_searches,
    list_search_history,
    list_watched_companies,
    log_search,
    remove_watched_company,
    save_jobs,
    save_search,
    set_status,
    toggle_favorite,
)
from app.models import ContactInfo, Experience, Profile, SkillGroup


class TestJobSearch(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_jobs.db"
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Ahmet Yılmaz",
                title="Eczane Teknisyeni",
                email="ahmet@example.com",
            ),
            skills=[
                SkillGroup(category="Uzmanlık", items=["Medula", "Reçete karşılama", "Stok takibi"]),
            ],
            experience=[
                Experience(
                    company="Şifa Eczanesi",
                    role="Teknisyen",
                    start_date="2022-01",
                    tech_stack=["Eczane otomasyonu"],
                )
            ],
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_count_jobs(self):
        df1 = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                    "location": "Kadıköy, İstanbul",
                    "description": "Medula bilen teknisyen",
                },
                {
                    "job_url": "https://example.com/job2",
                    "site": "indeed",
                    "title": "Ofis Asistanı",
                    "company": "Klinik A.Ş.",
                    "location": "Beşiktaş, İstanbul",
                    "description": "Genel ofis işleri",
                },
            ]
        )
        new_count1 = save_jobs(df1, self.db_path, self.profile)
        self.assertEqual(new_count1, 2)

        # Tekrar aynı işi ve 1 yeni işi kaydedince sadece yeni olan 1 sayılmalı
        df2 = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                    "location": "Kadıköy, İstanbul",
                    "description": "Medula ve reçete karşılama bilen teknisyen",
                },
                {
                    "job_url": "https://example.com/job3",
                    "site": "glassdoor",
                    "title": "Depo Sorumlusu",
                    "company": "İlaç Deposu",
                    "location": "Ümraniye, İstanbul",
                    "description": "Stok takibi",
                },
            ]
        )
        new_count2 = save_jobs(df2, self.db_path, self.profile)
        self.assertEqual(new_count2, 1)

        # Açıklamanın zenginleştirildiğini doğrula
        job1 = get_job(self.db_path, "https://example.com/job1")
        self.assertIn("reçete karşılama", job1["description"])

    def test_status_update_and_stats(self):
        df = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                }
            ]
        )
        save_jobs(df, self.db_path)
        set_status(self.db_path, "https://example.com/job1", "başvuruldu", notes="CV gönderildi")

        job = get_job(self.db_path, "https://example.com/job1")
        self.assertEqual(job["status"], "başvuruldu")
        self.assertEqual(job["notes"], "CV gönderildi")

        stats = get_stats(self.db_path)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["by_status"]["başvuruldu"], 1)

    def test_match_score_and_skills(self):
        text = "Eczanemize Medula ve reçete karşılama konularında deneyimli personel"
        matched = get_matched_skills(text, self.profile)
        self.assertIn("medula", matched)
        self.assertIn("reçete", matched)

        score = _match_score(text, {"medula", "reçete", "stok"})
        self.assertIsNotNone(score)
        self.assertGreater(score, 0.0)

    def test_favorite_and_salary(self):
        df = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                    "min_amount": 25000,
                    "max_amount": 35000,
                    "currency": "TRY",
                    "interval": "monthly",
                    "is_remote": False,
                }
            ]
        )
        save_jobs(df, self.db_path)
        job = get_job(self.db_path, "https://example.com/job1")
        self.assertEqual(job["min_amount"], 25000)
        self.assertEqual(job["currency"], "TRY")
        self.assertEqual(job["favorite"], 0)

        toggle_favorite(self.db_path, "https://example.com/job1", True)
        favs = list_jobs(self.db_path, favorite_only=True)
        self.assertEqual(len(favs), 1)

    def test_saved_searches(self):
        save_search(self.db_path, "eczane_ist", "Eczane Teknisyeni", "Istanbul", ["linkedin", "indeed"])
        searches = list_saved_searches(self.db_path)
        self.assertEqual(len(searches), 1)
        self.assertEqual(searches[0]["name"], "eczane_ist")

        deleted = delete_saved_search(self.db_path, "eczane_ist")
        self.assertTrue(deleted)
        self.assertEqual(len(list_saved_searches(self.db_path)), 0)

    def test_search_log(self):
        log_search(self.db_path, "Eczane Teknisyeni", "Istanbul", ["linkedin"], 12)
        history = list_search_history(self.db_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["result_count"], 12)

    def test_company_watchlist(self):
        add_watched_company(self.db_path, "Acme", "Eczane Teknisyeni")
        watched = list_watched_companies(self.db_path)
        self.assertEqual(len(watched), 1)
        self.assertEqual(watched[0]["company"], "Acme")

        removed = remove_watched_company(self.db_path, "Acme")
        self.assertTrue(removed)
        self.assertEqual(len(list_watched_companies(self.db_path)), 0)


if __name__ == "__main__":
    unittest.main()
