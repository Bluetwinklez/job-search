from datetime import datetime
import unittest

from app.calendar_export import generate_ics_event


class TestCalendarExport(unittest.TestCase):
    def test_generate_ics_event_structure(self):
        start_time = datetime(2026, 10, 15, 14, 30)
        ics_text = generate_ics_event(
            title="Kıdemli Python Geliştirici",
            company="Acme Corp",
            start_time=start_time,
            duration_minutes=60,
            location_or_url="https://meet.google.com/abc-defg-hij",
            notes="Teknik mülakat 1. aşama",
        )
        self.assertIn("BEGIN:VCALENDAR", ics_text)
        self.assertIn("BEGIN:VEVENT", ics_text)
        self.assertIn("SUMMARY:Mülakat: Kıdemli Python Geliştirici — Acme Corp", ics_text)
        self.assertIn("DTSTART:20261015T143000", ics_text)
        self.assertIn("DTEND:20261015T153000", ics_text)
        self.assertIn("LOCATION:https://meet.google.com/abc-defg-hij", ics_text)
        self.assertIn("Teknik mülakat 1. aşama", ics_text)
        self.assertIn("END:VEVENT", ics_text)
        self.assertIn("END:VCALENDAR", ics_text)


if __name__ == "__main__":
    unittest.main()
