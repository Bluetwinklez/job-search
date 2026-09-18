import unittest

from app.interview_prep import generate_baseline_interview_prep, generate_mock_interview
from app.models import ContactInfo, Experience, Profile, SkillGroup


class TestInterviewPrep(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Zeynep Kaya",
                title="Frontend Developer",
                email="zeynep@example.com",
            ),
            skills=[
                SkillGroup(category="Frontend", items=["React", "TypeScript", "Tailwind CSS"]),
            ],
            experience=[
                Experience(
                    company="Web Çözümleri A.Ş.",
                    role="Frontend Developer",
                    start_date="2022-01",
                    highlights=["React ile kullanıcı panelini yeniledi"],
                    tech_stack=["React", "TypeScript"],
                )
            ],
        )

    def test_baseline_interview_prep(self):
        result = generate_baseline_interview_prep(
            self.profile,
            job_title="React Developer",
            company="Global Tech",
            job_description="React ve TypeScript bilen tecrübeli yazılımcı",
        )
        self.assertGreaterEqual(len(result.questions), 4)
        self.assertGreaterEqual(len(result.key_strengths), 2)
        categories = [q.category for q in result.questions]
        self.assertIn("Teknik/Rol Odaklı", categories)
        self.assertIn("Davranışsal (STAR)", categories)
        self.assertIn("İşverene Sorulacak Soru", categories)

    def test_mock_interview_fallback(self):
        # API anahtarı yokken zarif fallback çalışmalı
        result = generate_mock_interview(
            self.profile,
            job_title="Frontend Developer",
            company="Startup Inc",
            api_key=None,
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("Startup Inc" in q.question or "Frontend" in q.question for q in result.questions))


if __name__ == "__main__":
    unittest.main()
