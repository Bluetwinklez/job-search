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
    get_job,
    get_matched_skills,
    get_stats,
    list_jobs,
    save_jobs,
    set_status,
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


if __name__ == "__main__":
    unittest.main()
