import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.job_search import save_jobs, set_interview_datetime
from app.notifications import build_daily_digest, send_email_notification, send_telegram_message

try:
    import pandas as pd

    def create_df(records):
        return pd.DataFrame(records)
except ImportError:
    class MockDataFrame:
        def __init__(self, records):
            self.records = records

        def to_dict(self, orient="records"):
            return self.records

    def create_df(records):
        return MockDataFrame(records)


class TestNotifications(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_jobs.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_daily_digest_empty(self):
        digest = build_daily_digest(self.db_path)
        self.assertIn("Günlük Özet", digest)
        self.assertIn("Takip zamanı gelmiş başvuru yok", digest)

    def test_build_daily_digest_with_upcoming_interview(self):
        from datetime import datetime, timedelta

        df = create_df(
            [
                {
                    "job_url": "https://example.com/job1",
                    "site": "linkedin",
                    "title": "Eczane Teknisyeni",
                    "company": "Merkez Eczane",
                }
            ]
        )
        save_jobs(df, self.db_path)
        soon = (datetime.now() + timedelta(days=1)).isoformat()
        set_interview_datetime(self.db_path, "https://example.com/job1", soon)

        digest = build_daily_digest(self.db_path)
        self.assertIn("Eczane Teknisyeni", digest)
        self.assertIn("Merkez Eczane", digest)

    @patch("urllib.request.urlopen")
    def test_send_telegram_message(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"{}"
        send_telegram_message("fake-token", "12345", "test message")
        mock_urlopen.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_email_notification(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        send_email_notification(
            "smtp.example.com", 587, "user@example.com", "pass", "to@example.com", "Subject", "Body"
        )
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "pass")
        mock_server.sendmail.assert_called_once()


if __name__ == "__main__":
    unittest.main()
