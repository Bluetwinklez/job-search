import unittest

from app.ats_scorer import score_profile
from app.models import ContactInfo, Education, Experience, Profile, SkillGroup


class TestATSScorer(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Ahmet Yılmaz",
                title="Backend Developer",
                email="ahmet@example.com",
                phone="+90 555 123 4567",
                location="İstanbul, Türkiye",
                linkedin="linkedin.com/in/ahmetyilmaz",
            ),
            summary="5 yıllık deneyime sahip, mikroservis mimarileri ve yüksek trafikli sistemler konusunda uzmanlaşmış backend geliştirici.",
            experience=[
                Experience(
                    company="Teknoloji A.Ş.",
                    role="Kıdemli Geliştirici",
                    start_date="2021-01",
                    highlights=[
                        "Mikroservis geçişini yönetti ve gecikmeyi %40 azalttı.",
                        "5 kişilik ekibe liderlik ederek projeyi 3 ay erken tamamladı.",
                    ],
                    tech_stack=["Python", "PostgreSQL", "Docker"],
                )
            ],
            education=[
                Education(school="İTÜ", degree="Lisans", field="Bilgisayar Müh.", start_date="2016", end_date="2020")
            ],
            skills=[
                SkillGroup(category="Diller", items=["Python", "Go", "SQL", "TypeScript"]),
                SkillGroup(category="Araçlar", items=["Docker", "Kubernetes", "Git", "Redis"]),
            ],
            certifications=["AWS Solutions Architect"],
        )

    def test_high_quality_profile_score(self):
        report = score_profile(self.profile)
        self.assertGreaterEqual(report.total_score, 85)
        self.assertGreaterEqual(report.metric_mentions_count, 2)
        self.assertTrue(len(report.strengths) > 0)

    def test_empty_profile_recommendations(self):
        empty_prof = Profile(
            contact=ContactInfo(
                full_name="Ali",
                title="Stajyer",
                email="ali@example.com",
            )
        )
        report = score_profile(empty_prof)
        self.assertLess(report.total_score, 50)
        self.assertTrue(any("Özet" in r for r in report.recommendations))
        self.assertTrue(any("deneyim" in r for r in report.recommendations))


if __name__ == "__main__":
    unittest.main()
