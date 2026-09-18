import unittest

from app.matching import contains_keyword, extract_matching_keywords, split_keywords, turkish_lower


class TestMatching(unittest.TestCase):
    def test_turkish_lower(self):
        self.assertEqual(turkish_lower("İLAÇ"), "ilaç")
        self.assertEqual(turkish_lower("IŞIK"), "ışık")
        self.assertEqual(turkish_lower("İSTANBUL"), "istanbul")
        self.assertEqual(turkish_lower(""), "")

    def test_contains_keyword_turkish_case(self):
        self.assertTrue(contains_keyword("İLAÇ DANIŞMANLIĞI", "ilaç"))
        self.assertTrue(contains_keyword("İstanbul içi etkinlik", "istanbul"))
        self.assertTrue(contains_keyword("IŞIK ve Ses Teknisyeni", "ışık"))
        self.assertTrue(contains_keyword("Medula Eczane Sistemi", "medula"))

    def test_contains_keyword_word_boundary(self):
        self.assertFalse(contains_keyword("Geliştiricilik", "geliştirici"))
        self.assertTrue(contains_keyword("Python geliştirici aranıyor", "python"))
        self.assertTrue(contains_keyword("C++ Developer", "c++"))

    def test_split_keywords(self):
        words = split_keywords("Reçete Karşılama ve Danışmanlık")
        self.assertIn("reçete", words)
        self.assertIn("karşılama", words)
        self.assertIn("danışmanlık", words)
        self.assertNotIn("ve", words)  # stopword

    def test_extract_matching_keywords(self):
        text = "Eczanemize Medula bilen ve reçete karşılayabilecek personel arıyoruz."
        keywords = {"medula", "reçete", "python", "docker"}
        matched = extract_matching_keywords(text, keywords)
        self.assertIn("medula", matched)
        self.assertIn("reçete", matched)
        self.assertNotIn("python", matched)


if __name__ == "__main__":
    unittest.main()
