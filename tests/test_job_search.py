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
    delete_interview_question,
    delete_saved_search,
    get_job,
    get_matched_skills,
    get_stats,
    list_interview_questions,
    list_jobs,
    list_saved_searches,
    list_search_history,
    list_upcoming_interviews,
    list_watched_companies,
    log_search,
    remove_watched_company,
    save_interview_questions,
    save_jobs,
    save_search,
    set_interview_datetime,
    set_status,
    toggle_favorite,
    update_interview_answer,
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


    def test_blacklist_operations(self):
        from app.job_search import (
            add_to_blacklist,
            get_blacklist,
            remove_from_blacklist,
            is_blacklisted,
        )

        # Ekleme
        self.assertTrue(add_to_blacklist(self.db_path, "İstenmeyen Şirket", kind="company"))
        self.assertTrue(add_to_blacklist(self.db_path, "Stajyer", kind="keyword"))
        # Tekrar ekleme False döner
        self.assertFalse(add_to_blacklist(self.db_path, "İstenmeyen Şirket", kind="company"))

        items = get_blacklist(self.db_path)
        self.assertEqual(len(items), 2)

        # Kontrol
        self.assertTrue(is_blacklisted("İstenmeyen Şirket A.Ş.", "Geliştirici", items))
        self.assertTrue(is_blacklisted("Normal Şirket", "Yazılım Stajyeri", items))
        self.assertFalse(is_blacklisted("İyi Şirket", "Kıdemli Geliştirici", items))

        # Silme
        self.assertTrue(remove_from_blacklist(self.db_path, "İstenmeyen Şirket"))
        self.assertEqual(len(get_blacklist(self.db_path)), 1)

    def test_list_jobs_with_blacklist_filter(self):
        from app.job_search import add_to_blacklist

        df = create_df(
            [
                {
                    "job_url": "https://example.com/clean1",
                    "title": "Backend Geliştirici",
                    "company": "Harika Teknoloji",
                },
                {
                    "job_url": "https://example.com/spam1",
                    "title": "Backend Geliştirici",
                    "company": "Kara Liste Şirketi",
                },
            ]
        )
        save_jobs(df, self.db_path)
        add_to_blacklist(self.db_path, "Kara Liste Şirketi", kind="company")

        # filter_blacklisted=True iken filtrelenmeli
        clean_jobs = list_jobs(self.db_path, filter_blacklisted=True)
        companies = [j["company"] for j in clean_jobs]
        self.assertNotIn("Kara Liste Şirketi", companies)
        self.assertIn("Harika Teknoloji", companies)

        # filter_blacklisted=False iken ikisi de gelmeli
        all_jobs = list_jobs(self.db_path, filter_blacklisted=False)
        self.assertEqual(len(all_jobs), 2)

    def test_interview_question_bank(self):
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

        questions = [
            {
                "category": "Teknik/Rol Odaklı",
                "question": "Medula sistemiyle ilgili deneyiminiz nedir?",
                "rationale": "Teknik yeterliliği ölçmek için.",
                "answer_tip": "Şifa Eczanesi'ndeki deneyiminizi anlatın.",
            }
        ]
        save_interview_questions(self.db_path, "https://example.com/job1", questions)

        bank = list_interview_questions(self.db_path)
        self.assertEqual(len(bank), 1)
        self.assertEqual(bank[0]["question"], "Medula sistemiyle ilgili deneyiminiz nedir?")
        self.assertIsNone(bank[0]["personal_answer"])

        filtered = list_interview_questions(self.db_path, job_url="https://example.com/job1")
        self.assertEqual(len(filtered), 1)

        updated = update_interview_answer(self.db_path, bank[0]["id"], "3 yıl Medula deneyimim var.")
        self.assertTrue(updated)
        refreshed = list_interview_questions(self.db_path)
        self.assertEqual(refreshed[0]["personal_answer"], "3 yıl Medula deneyimim var.")

        deleted = delete_interview_question(self.db_path, bank[0]["id"])
        self.assertTrue(deleted)
        self.assertEqual(len(list_interview_questions(self.db_path)), 0)

    def test_upcoming_interviews(self):
        from datetime import datetime, timedelta

        df = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                },
                {
                    "job_url": "https://example.com/job2",
                    "site": "linkedin",
                    "title": "Depo Sorumlusu",
                    "company": "İlaç Deposu",
                },
            ]
        )
        save_jobs(df, self.db_path)

        soon = (datetime.now() + timedelta(days=1)).isoformat()
        far = (datetime.now() + timedelta(days=30)).isoformat()
        set_interview_datetime(self.db_path, "https://example.com/job1", soon)
        set_interview_datetime(self.db_path, "https://example.com/job2", far)

        upcoming = list_upcoming_interviews(self.db_path, within_days=3)
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0]["job_url"], "https://example.com/job1")


if __name__ == "__main__":
    unittest.main()

