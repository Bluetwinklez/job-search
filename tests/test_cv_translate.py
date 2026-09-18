import unittest

from app.cv_translate import translate_profile_to_english
from app.models import ContactInfo, Profile


class TestCVTranslate(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Ayşe Kaya",
                title="Yazılım Mühendisi",
                email="ayse@example.com",
            ),
            summary="Deneyimli tam yığın geliştirici.",
        )

    def test_missing_api_key_raises(self):
        with self.assertRaises(ValueError):
            translate_profile_to_english(self.profile, api_key=None)


if __name__ == "__main__":
    unittest.main()
