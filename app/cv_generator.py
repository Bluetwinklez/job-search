"""Profil verisinden PDF CV üretimi.

Kullanım:
    python -m app.cv_generator --profile data/profile.example.json --output cv.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fpdf import FPDF

from app.models import Profile

ACCENT_COLOR = (30, 60, 114)
TEXT_COLOR = (30, 30, 30)
MUTED_COLOR = (100, 100, 100)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILY = "DejaVu"


class CVDocument(FPDF):
    def section_title(self, title: str) -> None:
        self.set_font(FONT_FAMILY, "B", 12)
        self.set_text_color(*ACCENT_COLOR)
        self.ln(4)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT_COLOR)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_text_color(*TEXT_COLOR)


def build_cv(profile: Profile) -> FPDF:
    pdf = CVDocument(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font(FONT_FAMILY, "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font(FONT_FAMILY, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(18, 15, 18)

    # Başlık / iletişim bilgileri
    pdf.set_font(FONT_FAMILY, "B", 20)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(0, 10, profile.contact.full_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.set_text_color(*MUTED_COLOR)
    pdf.cell(0, 7, profile.contact.title, new_x="LMARGIN", new_y="NEXT")

    contact_parts = [
        p
        for p in [
            profile.contact.email,
            profile.contact.phone,
            profile.contact.location,
            profile.contact.linkedin,
            profile.contact.github,
            profile.contact.website,
        ]
        if p
    ]
    pdf.set_font(FONT_FAMILY, "", 9)
    pdf.multi_cell(0, 6, "  |  ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*TEXT_COLOR)

    if profile.summary:
        pdf.section_title("Özet")
        pdf.set_font(FONT_FAMILY, "", 10)
        pdf.multi_cell(0, 5.5, profile.summary, new_x="LMARGIN", new_y="NEXT")

    if profile.experience:
        pdf.section_title("Deneyim")
        for exp in profile.experience:
            pdf.set_font(FONT_FAMILY, "B", 10.5)
            date_range = f"{exp.start_date} - {exp.end_date or 'Halen'}"
            pdf.multi_cell(0, 6, f"{exp.role} — {exp.company}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*MUTED_COLOR)
            location = f" | {exp.location}" if exp.location else ""
            pdf.cell(0, 5, f"{date_range}{location}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT_COLOR)
            pdf.set_font(FONT_FAMILY, "", 9.5)
            for point in exp.highlights:
                pdf.multi_cell(0, 5, f"- {point}", new_x="LMARGIN", new_y="NEXT")
            if exp.tech_stack:
                pdf.set_font(FONT_FAMILY, "", 9)
                pdf.set_text_color(*MUTED_COLOR)
                pdf.multi_cell(0, 5, "Teknolojiler: " + ", ".join(exp.tech_stack), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*TEXT_COLOR)
            pdf.ln(2)

    if profile.education:
        pdf.section_title("Eğitim")
        for edu in profile.education:
            pdf.set_font(FONT_FAMILY, "B", 10.5)
            field = f" - {edu.field}" if edu.field else ""
            pdf.multi_cell(0, 6, f"{edu.degree}{field}, {edu.school}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*MUTED_COLOR)
            pdf.cell(0, 5, f"{edu.start_date} - {edu.end_date or 'Halen'}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT_COLOR)
            pdf.ln(1)

    if profile.skills:
        pdf.section_title("Yetenekler")
        pdf.set_font(FONT_FAMILY, "", 9.5)
        for group in profile.skills:
            pdf.multi_cell(0, 5.5, f"{group.category}: {', '.join(group.items)}", new_x="LMARGIN", new_y="NEXT")

    if profile.languages:
        pdf.section_title("Diller")
        pdf.set_font(FONT_FAMILY, "", 9.5)
        pdf.multi_cell(0, 5.5, ", ".join(profile.languages), new_x="LMARGIN", new_y="NEXT")

    return pdf


def generate_cv(profile_path: Path, output_path: Path) -> None:
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = Profile.model_validate(data)
    pdf = build_cv(profile)
    pdf.output(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Profil JSON dosyasından PDF CV üretir.")
    parser.add_argument("--profile", type=Path, required=True, help="Profil JSON dosyası yolu")
    parser.add_argument("--output", type=Path, default=Path("cv.pdf"), help="Çıktı PDF yolu")
    args = parser.parse_args()

    generate_cv(args.profile, args.output)
    print(f"CV oluşturuldu: {args.output}")


if __name__ == "__main__":
    main()
