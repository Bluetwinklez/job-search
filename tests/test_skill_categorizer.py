import unittest
from app.models import ContactInfo, Experience, Profile, SkillGroup
from app.skill_categorizer import categorize_skills, extract_skills_from_profile


class TestSkillCategorizer(unittest.TestCase):
    def test_categorize_skills(self):
        raw = ["React", "Python", "Docker", "PostgreSQL", "Flutter", "Photoshop", "FastAPI"]
        groups = categorize_skills(raw)

        categories = {g.category: g.items for g in groups}
        self.assertIn("Frontend", categories)
        self.assertIn("React", categories["Frontend"])

        self.assertIn("Backend", categories)
        self.assertIn("Python", categories["Backend"])
        self.assertIn("FastAPI", categories["Backend"])

        self.assertIn("Bulut & DevOps", categories)
        self.assertIn("Docker", categories["Bulut & DevOps"])

        self.assertIn("Veritabanı & Depolama", categories)
        self.assertIn("PostgreSQL", categories["Veritabanı & Depolama"])

        self.assertIn("Mobil", categories)
        self.assertIn("Flutter", categories["Mobil"])

        self.assertIn("Diğer Yetenekler", categories)
        self.assertIn("Photoshop", categories["Diğer Yetenekler"])

    def test_extract_skills_from_profile(self):
        profile = Profile(
            contact=ContactInfo(
                full_name="Mehmet Demir",
                title="Fullstack Dev",
                email="mehmet@example.com",
            ),
            skills=[
                SkillGroup(category="Backend", items=["Python"]),
            ],
            experience=[
                Experience(
                    company="TechCorp",
                    role="Dev",
                    start_date="2020",
                    tech_stack=["Python", "FastAPI", "Redis", "Docker"],
                )
            ],
        )

        extracted = extract_skills_from_profile(profile)
        # Python is already in skills, so it shouldn't be suggested
        self.assertNotIn("Python", extracted)
        self.assertIn("FastAPI", extracted)
        self.assertIn("Redis", extracted)
        self.assertIn("Docker", extracted)


if __name__ == "__main__":
    unittest.main()
