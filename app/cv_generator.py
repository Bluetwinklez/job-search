"""Profil verisinden PDF CV üretimi.

Tasarım tercihleri bilinçli olarak sade tutulmuştur: tek sütun, tablo/ikon
yok, standart yazı tipi. Bu, hem ATS (başvuru takip sistemi) yazılımlarının
metni hatasız ayrıştırmasını hem de işe alım uzmanının CV'yi hızlıca
taramasını sağlar. Görsel kimlik, renk vurgusu ve boşluklandırma ile
oluşturulur; grafik veya gömülü metin görseli kullanılmaz.

Kullanım:
    python -m app.cv_generator --profile data/profile.example.json --output cv.pdf
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from fpdf import FPDF

from app.models import Profile

ACCENT_COLOR = (28, 56, 111)
ACCENT_TINT = (232, 236, 245)
TEXT_COLOR = (35, 35, 38)
MUTED_COLOR = (108, 112, 122)
DIVIDER_COLOR = (222, 225, 232)

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILY = "DejaVu"

MARGIN = 18


class CVDocument(FPDF):
    def section_title(self, title: str) -> None:
        self.ln(3)
        band_h = 7.5
        if self.get_y() + band_h > self.page_break_trigger:
            self.add_page()
        band_y = self.get_y()
        self.set_fill_color(*ACCENT_TINT)
        self.rect(self.l_margin, band_y, self.w - self.l_margin - self.r_margin, band_h, "F")
        self.set_xy(self.l_margin + 2, band_y)
        self.set_font(FONT_FAMILY, "B", 10.5)
        self.set_text_color(*ACCENT_COLOR)
        self.cell(0, band_h, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_y(band_y + band_h + 3)
        self.set_text_color(*TEXT_COLOR)

    def divider(self) -> None:
        self.set_draw_color(*DIVIDER_COLOR)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2.5)


def build_cv(profile: Profile) -> FPDF:
    pdf = CVDocument(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font(FONT_FAMILY, "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font(FONT_FAMILY, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN - 3, MARGIN)

    # Başlık / iletişim bilgileri
    pdf.set_font(FONT_FAMILY, "B", 22)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(0, 10, profile.contact.full_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.set_text_color(*MUTED_COLOR)
    pdf.cell(0, 6.5, profile.contact.title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

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
    pdf.set_text_color(*TEXT_COLOR)
    pdf.multi_cell(0, 5.5, "   ·   ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_draw_color(*ACCENT_COLOR)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_line_width(0.2)

    if profile.summary:
        pdf.section_title("Özet")
        pdf.set_font(FONT_FAMILY, "", 10)
        pdf.multi_cell(0, 5.5, profile.summary, new_x="LMARGIN", new_y="NEXT")

    if profile.experience:
        pdf.section_title("Deneyim")
        for i, exp in enumerate(profile.experience):
            if i > 0:
                pdf.divider()
            pdf.set_font(FONT_FAMILY, "B", 11)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.multi_cell(0, 6, exp.role, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*ACCENT_COLOR)
            location = f"  ·  {exp.location}" if exp.location else ""
            pdf.multi_cell(0, 5.5, f"{exp.company}{location}", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*MUTED_COLOR)
            date_range = f"{exp.start_date} - {exp.end_date or 'Halen'}"
            pdf.cell(0, 5.5, date_range, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)

            pdf.set_font(FONT_FAMILY, "", 9.5)
            pdf.set_text_color(*TEXT_COLOR)
            for point in exp.highlights:
                pdf.set_x(pdf.l_margin)
                pdf.cell(4, 5, "-", new_x="RIGHT", new_y="TOP")
                pdf.multi_cell(0, 5, point, new_x="LMARGIN", new_y="NEXT")
            if exp.tech_stack:
                pdf.set_font(FONT_FAMILY, "", 9)
                pdf.set_text_color(*MUTED_COLOR)
                pdf.multi_cell(0, 5, "Teknolojiler: " + ", ".join(exp.tech_stack), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*TEXT_COLOR)
            pdf.ln(1.5)

    if profile.education:
        pdf.section_title("Eğitim")
        for i, edu in enumerate(profile.education):
            if i > 0:
                pdf.ln(1)
            pdf.set_font(FONT_FAMILY, "B", 10.5)
            pdf.set_text_color(*TEXT_COLOR)
            field = f" - {edu.field}" if edu.field else ""
            pdf.multi_cell(0, 6, f"{edu.degree}{field}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*ACCENT_COLOR)
            pdf.multi_cell(0, 5.5, edu.school, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*MUTED_COLOR)
            pdf.cell(0, 5.5, f"{edu.start_date} - {edu.end_date or 'Halen'}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT_COLOR)

    if profile.skills:
        pdf.section_title("Yetenekler")
        for group in profile.skills:
            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.write(5.5, f"{group.category}: ")
            pdf.set_font(FONT_FAMILY, "", 9.5)
            pdf.set_text_color(*MUTED_COLOR)
            pdf.write(5.5, ", ".join(group.items))
            pdf.ln(6.5)
            pdf.set_text_color(*TEXT_COLOR)

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
