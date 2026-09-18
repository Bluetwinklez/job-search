import json
import unittest
from pathlib import Path

from app.models import ContactInfo, Education, Experience, Profile, SkillGroup


class TestModels(unittest.TestCase):
    def test_example_profile_loads(self):
        example_path = Path("data/profile.example.json")
        self.assertTrue(example_path.exists())
        data = json.loads(example_path.read_text(encoding="utf-8"))
        profile = Profile.model_validate(data)
        self.assertEqual(profile.contact.full_name, "Ahmet Yılmaz")
        self.assertTrue(len(profile.experience) > 0)
        self.assertTrue(len(profile.education) > 0)
        self.assertTrue(len(profile.skills) > 0)

    def test_contact_info_validation(self):
        contact = ContactInfo(
            full_name="Fatma Demir",
            title="Frontend Developer",
            email="fatma@example.com",
            phone="+90 555 123 4567",
        )
        self.assertEqual(contact.full_name, "Fatma Demir")

    def test_profile_defaults(self):
        profile = Profile(
            contact=ContactInfo(
                full_name="Test User",
                title="Tester",
                email="test@test.com",
            )
        )
        self.assertEqual(profile.experience, [])
        self.assertEqual(profile.education, [])
        self.assertEqual(profile.skills, [])
        self.assertEqual(profile.languages, [])


if __name__ == "__main__":
    unittest.main()
