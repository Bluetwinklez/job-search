import unittest
from app.models import ContactInfo, Experience, Profile, SkillGroup
from app.job_comparator import compare_jobs, format_salary


class TestJobComparator(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Fatma Kaya",
                title="Python Developer",
                email="fatma@example.com",
            ),
            skills=[
                SkillGroup(category="Backend", items=["Python", "FastAPI", "Docker", "PostgreSQL"]),
            ],
            experience=[
                Experience(
                    company="Alpha Yazılım",
                    role="Backend Dev",
                    start_date="2021-01",
                    tech_stack=["Redis", "Celery"],
                )
            ],
        )

        self.jobs = [
            {
                "job_url": "https://example.com/jobA",
                "title": "Senior Python Developer",
                "company": "Şirket A",
                "location": "İstanbul (Uzaktan)",
                "site": "linkedin",
                "status": "yeni",
                "min_amount": 90000,
                "max_amount": 120000,
                "currency": "TRY",
                "salary_interval": "aylık",
                "is_remote": 1,
                "match_score": 0.85,
                "description": "Python, FastAPI ve Docker tecrübesi arıyoruz.",
                "date_posted": "2026-09-10",
            },
            {
                "job_url": "https://example.com/jobB",
                "title": "Backend Yazılım Uzmanı",
                "company": "Şirket B",
                "location": "Ankara (Hibrit)",
                "site": "indeed",
                "status": "başvuruldu",
                "min_amount": None,
                "max_amount": None,
                "currency": None,
                "salary_interval": None,
                "is_remote": 0,
                "match_score": 0.60,
                "description": "Python, PostgreSQL ve Redis bilen.",
                "date_posted": "2026-09-12",
            },
        ]

    def test_format_salary(self):
        s1 = format_salary(80000, 100000, "TRY", "aylık")
        self.assertIn("80,000", s1)
        self.assertIn("100,000", s1)
        self.assertIn("TRY", s1)

        s2 = format_salary(None, None, None, None)
        self.assertEqual(s2, "Belirtilmemiş")

    def test_compare_jobs(self):
        res = compare_jobs(self.jobs, self.profile)
        self.assertEqual(len(res.columns), 2)
        col1 = res.columns[0]
        col2 = res.columns[1]

        self.assertEqual(col1.company, "Şirket A")
        self.assertEqual(col1.match_score, "%85")
        self.assertTrue(any("fastap" in s for s in col1.matched_skills))

        self.assertEqual(col2.company, "Şirket B")
        self.assertEqual(col2.match_score, "%60")
        self.assertTrue(any("redis" in s for s in col2.matched_skills))

        # Her iki ilanda da ortak eşleşen python olmalı
        self.assertTrue(any("python" in s for s in res.common_skills))
        self.assertIn("Şirket A", res.recommendation)


if __name__ == "__main__":
    unittest.main()
