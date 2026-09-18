import unittest
from app.markdown_generator import generate_markdown_cv
from app.models import ContactInfo, Education, Experience, Profile, SkillGroup


class TestMarkdownGenerator(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Gizem Arslan",
                title="Fullstack Developer",
                email="gizem@example.com",
                github="https://github.com/gizem",
                location="Ankara",
            ),
            summary="Deneyimli geliştirici.",
            experience=[
                Experience(
                    company="DataTech",
                    role="Senior Engineer",
                    start_date="2021-01",
                    highlights=["Mikroservis mimarisini kurdu"],
                    tech_stack=["Python", "Docker"],
                )
            ],
            education=[
                Education(school="ODTÜ", degree="Lisans", field="CENG", start_date="2016", end_date="2020")
            ],
            skills=[
                SkillGroup(category="Backend", items=["Python", "FastAPI"]),
            ],
            languages=["Türkçe", "İngilizce"],
        )

    def test_generate_markdown_cv(self):
        md = generate_markdown_cv(self.profile)
        self.assertIn("# Gizem Arslan", md)
        self.assertIn("Senior Engineer", md)
        self.assertIn("DataTech", md)
        self.assertIn("ODTÜ", md)
        self.assertIn("Python, FastAPI", md)
        self.assertIn("Türkçe, İngilizce", md)


if __name__ == "__main__":
    unittest.main()
