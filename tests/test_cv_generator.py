import json
import tempfile
import unittest
from pathlib import Path

from app.cover_letter import render_letter_pdf
from app.cv_generator import build_cv
from app.models import ContactInfo, Experience, Profile, SkillGroup


class TestCVGenerator(unittest.TestCase):
    def setUp(self):
        self.profile = Profile(
            contact=ContactInfo(
                full_name="Ayşe Kaya",
                title="Yazılım Mühendisi",
                email="ayse@example.com",
                phone="+90 555 987 6543",
                location="Ankara, Türkiye",
                github="github.com/aysekaya",
            ),
            summary="Deneyimli tam yığın geliştirici.",
            experience=[
                Experience(
                    company="Tekno A.Ş.",
                    role="Kıdemli Mühendis",
                    start_date="2021-03",
                    location="Ankara",
                    highlights=["Dağıtık sistemlerin mimarisini tasarladı", "Performansı %35 artırdı"],
                    tech_stack=["Python", "Go", "Docker"],
                )
            ],
            skills=[
                SkillGroup(category="Diller", items=["Python", "Go", "TypeScript"]),
                SkillGroup(category="Araçlar", items=["Docker", "Git", "Kubernetes"]),
            ],
            languages=["Türkçe (Anadil)", "İngilizce (İleri Düzey)"],
            certifications=["AWS Certified Solutions Architect"],
        )

    def test_build_cv_pdf(self):
        pdf = build_cv(self.profile)
        pdf_bytes = bytes(pdf.output())
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_build_cv_all_themes(self):
        from app.cv_generator import THEMES

        for theme_key in THEMES:
            pdf = build_cv(self.profile, theme=theme_key)
            pdf_bytes = bytes(pdf.output())
            self.assertGreater(len(pdf_bytes), 1000)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


    def test_build_cv_with_photo(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp_dir:
            photo_path = Path(tmp_dir) / "photo.jpg"
            Image.new("RGB", (100, 100), color=(100, 120, 140)).save(photo_path)

            pdf = build_cv(self.profile, photo_path=photo_path)
            pdf_bytes = bytes(pdf.output())
            self.assertGreater(len(pdf_bytes), 1000)
            self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_build_cv_english_labels(self):
        pdf = build_cv(self.profile, language="en")
        pdf_bytes = bytes(pdf.output())
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_render_cover_letter_pdf(self):
        letter_text = "Sayın Yetkili,\n\nPozisyon için başvurumu iletiyorum.\n\nSaygılarımla,\nAyşe Kaya"
        pdf = render_letter_pdf(letter_text)
        pdf_bytes = bytes(pdf.output())
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
