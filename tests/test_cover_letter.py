import unittest
from unittest.mock import patch

from app.cover_letter import (
    _latest_experience,
    _most_relevant_experience,
    generate_bulk_cover_letters,
    generate_cover_letter,
    generate_cover_letter_english,
)
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

    @patch("app.llm_client.generate_llm_response")
    def test_generate_cover_letter_english_uses_llm(self, mock_llm):
        mock_llm.return_value = "Dear Hiring Manager, ..."
        letter = generate_cover_letter_english(
            self.profile,
            job_title="Senior Python Developer",
            company="Teknoloji A.Ş.",
            job_description="Python ve Docker bilen adaylar",
            provider="anthropic",
            api_key="test-key",
        )
        self.assertEqual(letter, "Dear Hiring Manager, ...")
        mock_llm.assert_called_once()
        _, kwargs = mock_llm.call_args
        self.assertEqual(kwargs["provider"], "anthropic")
        self.assertIn("Do NOT invent", kwargs["system_prompt"])

    def test_generate_bulk_cover_letters_turkish(self):
        jobs = [
            {"job_url": "https://example.com/1", "title": "Backend Developer", "company": "Acme"},
            {"job_url": "https://example.com/2", "title": "Data Engineer", "company": "Globex"},
        ]
        letters = generate_bulk_cover_letters(self.profile, jobs, language="tr")
        self.assertEqual(len(letters), 2)
        self.assertIn("Acme", letters["https://example.com/1"])
        self.assertIn("Globex", letters["https://example.com/2"])

    @patch("app.llm_client.generate_llm_response")
    def test_generate_bulk_cover_letters_english(self, mock_llm):
        mock_llm.return_value = "Dear Hiring Manager, ..."
        jobs = [{"job_url": "https://example.com/1", "title": "Backend Developer", "company": "Acme"}]
        letters = generate_bulk_cover_letters(self.profile, jobs, language="en")
        self.assertEqual(letters["https://example.com/1"], "Dear Hiring Manager, ...")

    def test_render_letter_pdf_with_letterhead(self):
        from app.cover_letter import render_letter_pdf

        letter = "Sayın Yetkili,\n\nİlanınızla ilgileniyorum.\n\nSaygılarımla,\nMehmet Öz"
        # Profilsiz (eski uyumluluk)
        pdf1 = render_letter_pdf(letter)
        self.assertGreater(len(bytes(pdf1.output())), 1000)

        # Kurumsal antetli ve temalı
        pdf2 = render_letter_pdf(letter, profile=self.profile, theme="emerald_green")
        self.assertGreater(len(bytes(pdf2.output())), 1000)


if __name__ == "__main__":
    unittest.main()

