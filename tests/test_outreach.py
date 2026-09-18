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


if __name__ == "__main__":
    unittest.main()
