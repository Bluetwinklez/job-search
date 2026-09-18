import unittest
from pathlib import Path
import json

from app.models import Profile
from app.profile_editor import (
    parse_bullets,
    format_bullets,
    parse_comma_list,
    format_comma_list,
    profile_to_form_dict,
    form_dict_to_profile,
    create_blank_experience,
)


class TestProfileEditor(unittest.TestCase):
    def test_bullet_parsing_and_formatting(self):
        text = "• İlk madde\n- İkinci madde\n* Üçüncü madde\nDördüncü madde"
        bullets = parse_bullets(text)
        self.assertEqual(len(bullets), 4)
        self.assertEqual(bullets[0], "İlk madde")
        self.assertEqual(bullets[1], "İkinci madde")
        self.assertEqual(bullets[2], "Üçüncü madde")
        self.assertEqual(bullets[3], "Dördüncü madde")

        formatted = format_bullets(bullets)
        self.assertIn("• İlk madde", formatted)
        self.assertIn("• Dördüncü madde", formatted)

    def test_comma_list_parsing(self):
        text = "Python, FastAPI, Docker,   PostgreSQL  "
        items = parse_comma_list(text)
        self.assertEqual(items, ["Python", "FastAPI", "Docker", "PostgreSQL"])
        self.assertEqual(format_comma_list(items), "Python, FastAPI, Docker, PostgreSQL")

    def test_roundtrip_profile_conversion(self):
        example_path = Path("data/profile.example.json")
        self.assertTrue(example_path.exists())
        data = json.loads(example_path.read_text(encoding="utf-8"))
        original_profile = Profile.model_validate(data)

        form_data = profile_to_form_dict(original_profile)
        self.assertEqual(form_data["contact"]["full_name"], "Ahmet Yılmaz")
        self.assertTrue(len(form_data["experience"]) > 0)

        restored_profile = form_dict_to_profile(form_data)
        self.assertEqual(restored_profile.contact.full_name, original_profile.contact.full_name)
        self.assertEqual(restored_profile.contact.email, original_profile.contact.email)
        self.assertEqual(len(restored_profile.experience), len(original_profile.experience))
        self.assertEqual(len(restored_profile.skills), len(original_profile.skills))
        self.assertEqual(restored_profile.experience[0].company, original_profile.experience[0].company)

    def test_create_blank_experience(self):
        blank = create_blank_experience()
        self.assertIn("company", blank)
        self.assertIn("highlights", blank)


if __name__ == "__main__":
    unittest.main()
