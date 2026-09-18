import unittest
from pathlib import Path
import json

from app.models import Profile
from app.docx_generator import build_docx, get_docx_bytes


class TestDocxGenerator(unittest.TestCase):
    def test_build_docx_from_example(self):
        example_path = Path("data/profile.example.json")
        self.assertTrue(example_path.exists())
        data = json.loads(example_path.read_text(encoding="utf-8"))
        profile = Profile.model_validate(data)

        doc = build_docx(profile)
        self.assertTrue(len(doc.paragraphs) > 5)

        docx_bytes = get_docx_bytes(profile)
        self.assertGreater(len(docx_bytes), 2000)
        # DOCX dosyaları standart bir zip yapısına sahiptir ve ilk iki baytı PK'dir (b'PK')
        self.assertTrue(docx_bytes.startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
