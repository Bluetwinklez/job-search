import tempfile
import unittest
import zipfile
import io
from pathlib import Path

from app.backup import create_backup_zip, restore_backup_zip


class TestBackup(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.data_dir.mkdir()

        # Sahte dosyalar oluştur
        (self.data_dir / "jobs.db").write_text("fake db content", encoding="utf-8")
        profiles_dir = self.data_dir / "profiles"
        profiles_dir.mkdir()
        (profiles_dir / "yazilim.json").write_text('{"name": "test"}', encoding="utf-8")

        history_dir = self.data_dir / "profile_history" / "yazilim"
        history_dir.mkdir(parents=True)
        (history_dir / "20260918_backup.json").write_text('{"history": true}', encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_restore_backup(self):
        zip_bytes = create_backup_zip(self.data_dir)
        self.assertGreater(len(zip_bytes), 0)

        # Arşiv içeriğini doğrula
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            namelist = zf.namelist()
            self.assertIn("jobs.db", namelist)
            self.assertIn("profiles/yazilim.json", namelist)
            self.assertTrue(any("profile_history" in n for n in namelist))

        # Yeni bir hedef klasöre geri yükleme
        target_dir = Path(self.temp_dir.name) / "restored_data"
        res = restore_backup_zip(zip_bytes, target_dir)
        self.assertTrue(res["success"])
        self.assertIn("jobs.db", res["files_restored"])

        self.assertTrue((target_dir / "jobs.db").exists())
        self.assertEqual((target_dir / "jobs.db").read_text(encoding="utf-8"), "fake db content")
        self.assertTrue((target_dir / "profiles" / "yazilim.json").exists())

    def test_restore_invalid_zip(self):
        res = restore_backup_zip(b"not a valid zip", self.data_dir)
        self.assertFalse(res["success"])
        self.assertIn("Geçersiz", res["error"])


if __name__ == "__main__":
    unittest.main()
