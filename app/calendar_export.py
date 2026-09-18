"""Mülakatlar için standart iCalendar (.ics) takvim dosyası üretici."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid


def generate_ics_event(
    title: str,
    company: str,
    start_time: datetime,
    duration_minutes: int = 45,
    location_or_url: str | None = None,
    notes: str | None = None,
) -> str:
    """Mülakat için RFC 5545 uyumlu .ics takvim verisi üretir."""
    end_time = start_time + timedelta(minutes=duration_minutes)
    uid = f"{uuid.uuid4()}@is-arama-asistani"
    now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    fmt = "%Y%m%dT%H%M%S"
    dtstart_str = start_time.strftime(fmt)
    dtend_str = end_time.strftime(fmt)

    summary = f"Mülakat: {title} — {company}"
    description_lines = []
    if notes:
        description_lines.append(notes)
    if location_or_url:
        description_lines.append(f"Bağlantı / Konum: {location_or_url}")
    description = "\\n".join(description_lines)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//İş Arama Asistanı//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"DTSTART:{dtstart_str}",
        f"DTEND:{dtend_str}",
        f"SUMMARY:{summary}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location_or_url:
        lines.append(f"LOCATION:{location_or_url}")
    lines.extend([
        "STATUS:CONFIRMED",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])
    return "\r\n".join(lines)
