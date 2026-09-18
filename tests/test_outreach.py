import unittest

from app.models import ContactInfo, Experience, Profile, SkillGroup
from app.outreach import (
    generate_cold_email,
    generate_follow_up_email,
    generate_linkedin_connection_note,
    generate_thank_you_email,
)


class TestOutreach(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Barış Akın",
                title="Mobil Geliştirici",
                email="baris@example.com",
                phone="+90 555 111 2233",
            ),
            summary="Flutter ve iOS geliştirme uzmanı.",
            experience=[
                Experience(
                    company="AppStudio",
                    role="Mobil Geliştirici",
                    start_date="2021-01",
                    tech_stack=["Flutter", "Dart", "Swift"],
                )
            ],
        )

    def test_linkedin_note_length(self):
        note = generate_linkedin_connection_note(
            self.profile,
            job_title="Flutter Developer",
            company="Fintech Co",
            recipient_name="Ayşe Hanım",
        )
        self.assertLessEqual(len(note), 300)
        self.assertIn("Fintech Co", note)
        self.assertIn("Barış Akın", note)

    def test_cold_email_generation(self):
        subject, body = generate_cold_email(
            self.profile,
            job_title="Senior iOS Developer",
            company="Tech Corp",
        )
        self.assertIn("Senior iOS Developer Başvurusu", subject)
        self.assertIn("Tech Corp", body)
        self.assertIn("baris@example.com", body)

    def test_follow_up_email(self):
        subject, body = generate_follow_up_email(
            self.profile,
            job_title="iOS Developer",
            company="Mobile Ltd",
            days_ago=10,
        )
        self.assertIn("Takip:", subject)
        self.assertIn("10 gün önce", body)
        self.assertIn("Mobile Ltd", body)

    def test_thank_you_email(self):
        subject, body = generate_thank_you_email(
            self.profile,
            job_title="Flutter Dev",
            company="Startup A.Ş.",
            interviewer_name="Can Bey",
        )
        self.assertIn("Teşekkürler:", subject)
        self.assertIn("Can Bey", body)
        self.assertIn("Startup A.Ş.", body)

    def test_check_follow_up_needed(self):
        import tempfile
        import sqlite3
        from pathlib import Path
        from app.outreach import check_follow_up_needed

        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "test.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE jobs (job_url TEXT, title TEXT, company TEXT, site TEXT, fetched_at TEXT, status TEXT)")
            # 10 gün önce
            conn.execute("INSERT INTO jobs VALUES ('url1', 'Dev', 'Company A', 'linkedin', '2026-09-01T00:00:00+00:00', 'başvuruldu')")
            # 1 gün önce (henüz takip zamanı değil)
            conn.execute("INSERT INTO jobs VALUES ('url2', 'Dev', 'Company B', 'indeed', '2026-09-17T00:00:00+00:00', 'başvuruldu')")
            # 10 gün önce ama mülakat aşamasında
            conn.execute("INSERT INTO jobs VALUES ('url3', 'Dev', 'Company C', 'glassdoor', '2026-09-01T00:00:00+00:00', 'mülakat')")
            conn.commit()
            conn.close()

            needed = check_follow_up_needed(db, days_threshold=7)
            self.assertEqual(len(needed), 1)
            self.assertEqual(needed[0]["job_url"], "url1")
            self.assertEqual(needed[0]["company"], "Company A")


if __name__ == "__main__":
    unittest.main()

