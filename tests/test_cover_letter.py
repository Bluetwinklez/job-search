import unittest

from app.cover_letter import _latest_experience, _most_relevant_experience, generate_cover_letter
from app.models import ContactInfo, Experience, Profile, SkillGroup


class TestCoverLetter(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Mehmet Öz",
                title="Yazılım Geliştirici",
                email="mehmet@example.com",
            ),
            summary="Deneyimli backend geliştirici.",
            experience=[
                Experience(
                    company="Eski Şirket",
                    role="Stajyer",
                    start_date="2019-06",
                    end_date="2019-09",
                    highlights=["Veritabanı bakımı yaptı"],
                    tech_stack=["SQL"],
                ),
                Experience(
                    company="Yeni Şirket",
                    role="Kıdemli Geliştirici",
                    start_date="2022-01",
                    end_date=None,  # Halen
                    highlights=["Mikroservis mimarisine geçişi yönetti"],
                    tech_stack=["Python", "FastAPI", "Docker"],
                ),
            ],
            skills=[
                SkillGroup(category="Backend", items=["Python", "Docker", "PostgreSQL"]),
            ],
        )

    def test_latest_experience_selection(self):
        # Halen devam eden deneyimi seçmeli (ikinci eleman)
        latest = _latest_experience(self.profile)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.company, "Yeni Şirket")

    def test_most_relevant_experience_matching(self):
        # SQL arayan bir pozisyonda Eski Şirket daha alakalı
        relevant = _most_relevant_experience(self.profile, "Veritabanı Uzmanı", "SQL ve veritabanı bakımı")
        self.assertEqual(relevant.company, "Eski Şirket")

        # Docker arayan bir pozisyonda Yeni Şirket daha alakalı
        relevant_docker = _most_relevant_experience(self.profile, "Backend Dev", "FastAPI ve Docker deneyimi")
        self.assertEqual(relevant_docker.company, "Yeni Şirket")

    def test_generate_cover_letter_content(self):
        letter = generate_cover_letter(
            self.profile,
            job_title="Senior Python Developer",
            company="Teknoloji A.Ş.",
            job_description="Python ve Docker bilen adaylar",
        )
        self.assertIn("Sayın Yetkili,", letter)
        self.assertIn("Teknoloji A.Ş.", letter)
        self.assertIn("Senior Python Developer", letter)
        self.assertIn("Mehmet Öz", letter)
        self.assertIn("mehmet@example.com", letter)


if __name__ == "__main__":
    unittest.main()
