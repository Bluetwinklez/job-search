import unittest
from app.models import ContactInfo, Experience, Profile, SkillGroup
from app.ui_components import (
    calculate_profile_completeness,
    render_breadcrumb_html,
    render_empty_state_html,
    render_cv_html_preview,
    render_donut_chart_html,
)


class TestUIComponents(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Zeynep Kaya",
                title="Frontend Developer",
                email="zeynep@example.com",
                phone="+90 555 987 6543",
            ),
            summary="Deneyimli react geliştirici 5 yıllık tecrübe ile.",
            experience=[
                Experience(
                    company="WebLabs",
                    role="Frontend Dev",
                    start_date="2021-01",
                    highlights=["Performansı %50 artırdı"],
                    tech_stack=["React", "TypeScript"],
                )
            ],
            education=[],
            skills=[
                SkillGroup(category="Frontend", items=["React", "CSS", "HTML"]),
            ],
        )

    def test_completeness_calculation(self):
        score, missing = calculate_profile_completeness(self.profile)
        self.assertGreater(score, 50)
        self.assertTrue(any("Eğitim" in m for m in missing))

        score_none, missing_none = calculate_profile_completeness(None)
        self.assertEqual(score_none, 0)

    def test_breadcrumb_html(self):
        html = render_breadcrumb_html("yazilim", 85, 12)
        self.assertIn("yazilim", html)
        self.assertIn("%85", html)
        self.assertIn("12", html)

    def test_empty_state_html(self):
        html = render_empty_state_html("İlan Bulunamadı", "Lütfen arama terimlerinizi genişletin.")
        self.assertIn("İlan Bulunamadı", html)

    def test_cv_html_preview(self):
        html = render_cv_html_preview(self.profile, "modern_slate")
        self.assertIn("Zeynep Kaya", html)
        self.assertIn("WebLabs", html)
        self.assertIn("React", html)


    def test_donut_chart_html(self):
        data = {"yeni": 5, "başvuruldu": 3, "mülakat": 2, "teklif": 1, "reddedildi": 1}
        html = render_donut_chart_html(data, "Durum Dağılımı")
        self.assertIn("Durum Dağılımı", html)
        self.assertIn("12", html)  # total 12
        self.assertIn("Yeni", html)
        self.assertIn("Başvuruldu", html)

        empty_html = render_donut_chart_html({}, "Boş Veri")
        self.assertIn("Boş Veri", empty_html)


if __name__ == "__main__":
    unittest.main()
