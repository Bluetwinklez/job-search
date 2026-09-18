import unittest
from app.salary_estimator import estimate_salary


class TestSalaryEstimator(unittest.TestCase):
    def test_estimate_junior_backend(self):
        res = estimate_salary("Backend Developer", experience_level="junior", location="istanbul")
        self.assertEqual(res.role, "Backend Developer")
        self.assertEqual(res.experience_level, "junior")
        self.assertGreater(res.min_monthly, 0)
        self.assertGreater(res.max_monthly, res.min_monthly)
        self.assertEqual(res.currency, "TRY")
        self.assertEqual(len(res.negotiation_tips), 4)
        self.assertEqual(len(res.talking_points), 3)

    def test_estimate_senior_remote_usd(self):
        res = estimate_salary("DevOps Engineer", experience_level="senior", location="remote", currency="USD")
        self.assertEqual(res.currency, "USD")
        self.assertEqual(res.experience_level, "senior")
        self.assertGreater(res.median_monthly, 1000)
        self.assertIn("USD", res.market_insights)

    def test_talking_points_contain_numbers(self):
        res = estimate_salary("Frontend Developer", experience_level="mid", location="ankara")
        self.assertTrue(any(f"{res.min_monthly:,.0f}" in tp for tp in res.talking_points))


if __name__ == "__main__":
    unittest.main()
