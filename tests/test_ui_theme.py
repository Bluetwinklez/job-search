import unittest
from app.ui_theme import CUSTOM_CSS


class TestUITheme(unittest.TestCase):
    def test_custom_css_contents(self):
        self.assertIn("Plus Jakarta Sans", CUSTOM_CSS)
        self.assertIn("stMetric", CUSTOM_CSS)
        self.assertIn("stVerticalBlockBorderWrapper", CUSTOM_CSS)
        self.assertIn("@media (max-width: 768px)", CUSTOM_CSS)


if __name__ == "__main__":
    unittest.main()
