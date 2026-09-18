import json
import tempfile
import unittest
from pathlib import Path

from app import profile_store


class TestProfileStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_profiles_dir = profile_store.PROFILES_DIR
        self.original_history_dir = profile_store.HISTORY_DIR

        profile_store.PROFILES_DIR = Path(self.temp_dir.name) / "profiles"
        profile_store.HISTORY_DIR = Path(self.temp_dir.name) / "history"

    def tearDown(self):
        profile_store.PROFILES_DIR = self.original_profiles_dir
        profile_store.HISTORY_DIR = self.original_history_dir
        self.temp_dir.cleanup()

    def test_save_and_load_profile(self):
        data = {"contact": {"full_name": "Ahmet Yilmaz", "email": "ahmet@example.com"}}
        profile_store.save_profile("test_user", data)

        profiles = profile_store.list_profiles()
        self.assertIn("test_user", profiles)

        loaded_text = profile_store.load_profile_text("test_user")
        self.assertIsNotNone(loaded_text)
        self.assertIn("Ahmet Yilmaz", loaded_text)

    def test_clone_profile(self):
        data = {"contact": {"full_name": "Canan Ozturk", "email": "canan@example.com"}}
        profile_store.save_profile("original", data)

        success = profile_store.clone_profile("original", "original_clone")
        self.assertTrue(success)

        profiles = profile_store.list_profiles()
        self.assertIn("original", profiles)
        self.assertIn("original_clone", profiles)

        clone_text = profile_store.load_profile_text("original_clone")
        self.assertIn("Canan Ozturk", clone_text)

        # Cannot clone to already existing name
        self.assertFalse(profile_store.clone_profile("original", "original_clone"))
        # Cannot clone from nonexistent name
        self.assertFalse(profile_store.clone_profile("nonexistent", "new_name"))

    def test_delete_profile(self):
        data = {"contact": {"full_name": "Test"}}
        profile_store.save_profile("to_delete", data)
        self.assertTrue(profile_store.delete_profile("to_delete"))
        self.assertNotIn("to_delete", profile_store.list_profiles())
        self.assertFalse(profile_store.delete_profile("to_delete"))


if __name__ == "__main__":
    unittest.main()
