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

THEMES: dict[str, dict] = {
    "classic_navy": {
        "name": "Klasik Lacivert (Standart)",
        "accent": (28, 56, 111),
        "tint": (232, 236, 245),
        "text": (35, 35, 38),
        "muted": (108, 112, 122),
        "divider": (222, 225, 232),
    },
    "modern_slate": {
        "name": "Modern Grafit",
        "accent": (45, 55, 72),
        "tint": (237, 242, 247),
        "text": (26, 32, 44),
        "muted": (113, 128, 150),
        "divider": (226, 232, 240),
    },
    "emerald_green": {
        "name": "Zümrüt Yeşil",
        "accent": (20, 83, 45),
        "tint": (236, 253, 245),
        "text": (24, 24, 27),
        "muted": (100, 116, 139),
        "divider": (220, 235, 225),
    },
    "executive_burgundy": {
        "name": "Bordo / Yönetici",
        "accent": (120, 20, 40),
        "tint": (253, 242, 244),
        "text": (30, 25, 25),
        "muted": (120, 110, 110),
        "divider": (235, 220, 225),
    },
    "minimal_dark": {
        "name": "Minimalist Koyu",
        "accent": (30, 30, 32),
        "tint": (240, 240, 242),
        "text": (20, 20, 22),
        "muted": (100, 100, 105),
        "divider": (215, 215, 220),
    },
}

ACCENT_COLOR = THEMES["classic_navy"]["accent"]
ACCENT_TINT = THEMES["classic_navy"]["tint"]
TEXT_COLOR = THEMES["classic_navy"]["text"]
MUTED_COLOR = THEMES["classic_navy"]["muted"]
DIVIDER_COLOR = THEMES["classic_navy"]["divider"]

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILY = "DejaVu"

MARGIN = 18


class CVDocument(FPDF):
    def __init__(self, theme_colors: dict | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        colors = theme_colors or THEMES["classic_navy"]
        self.accent_color = colors["accent"]
        self.accent_tint = colors["tint"]
        self.text_color_val = colors["text"]
        self.muted_color = colors["muted"]
        self.divider_color = colors["divider"]

    def section_title(self, title: str) -> None:
        self.ln(3)
        band_h = 7.5
        if self.get_y() + band_h > self.page_break_trigger:
            self.add_page()
        band_y = self.get_y()
        self.set_fill_color(*self.accent_tint)
        self.rect(self.l_margin, band_y, self.w - self.l_margin - self.r_margin, band_h, "F")
        self.set_xy(self.l_margin + 2, band_y)
        self.set_font(FONT_FAMILY, "B", 10.5)
        self.set_text_color(*self.accent_color)
        self.cell(0, band_h, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_y(band_y + band_h + 3)
        self.set_text_color(*self.text_color_val)

    def divider(self) -> None:
        self.set_draw_color(*self.divider_color)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2.5)


def build_cv(profile: Profile, theme: str = "classic_navy") -> FPDF:
    colors = THEMES.get(theme, THEMES["classic_navy"])
    pdf = CVDocument(theme_colors=colors, format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_font(FONT_FAMILY, "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font(FONT_FAMILY, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN - 3, MARGIN)


    # Başlık / iletişim bilgileri
    pdf.set_font(FONT_FAMILY, "B", 22)
    pdf.set_text_color(*pdf.accent_color)
    pdf.cell(0, 10, profile.contact.full_name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT_FAMILY, "", 12)
    pdf.set_text_color(*pdf.muted_color)
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
    pdf.set_text_color(*pdf.text_color_val)
    pdf.multi_cell(0, 5.5, "   ·   ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_draw_color(*pdf.accent_color)
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
            pdf.set_text_color(*pdf.text_color_val)
            pdf.multi_cell(0, 6, exp.role, new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*pdf.accent_color)
            location = f"  ·  {exp.location}" if exp.location else ""
            pdf.multi_cell(0, 5.5, f"{exp.company}{location}", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*pdf.muted_color)
            date_range = f"{exp.start_date} - {exp.end_date or 'Halen'}"
            pdf.cell(0, 5.5, date_range, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)

            pdf.set_font(FONT_FAMILY, "", 9.5)
            pdf.set_text_color(*pdf.text_color_val)
            for point in exp.highlights:
                pdf.set_x(pdf.l_margin)
                pdf.cell(4, 5, "-", new_x="RIGHT", new_y="TOP")
                pdf.multi_cell(0, 5, point, new_x="LMARGIN", new_y="NEXT")
            if exp.tech_stack:
                pdf.set_font(FONT_FAMILY, "", 9)
                pdf.set_text_color(*pdf.muted_color)
                pdf.multi_cell(0, 5, "Teknolojiler: " + ", ".join(exp.tech_stack), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*pdf.text_color_val)
            pdf.ln(1.5)

    if profile.education:
        pdf.section_title("Eğitim")
        for i, edu in enumerate(profile.education):
            if i > 0:
                pdf.ln(1)
            pdf.set_font(FONT_FAMILY, "B", 10.5)
            pdf.set_text_color(*pdf.text_color_val)
            field = f" - {edu.field}" if edu.field else ""
            pdf.multi_cell(0, 6, f"{edu.degree}{field}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*pdf.accent_color)
            pdf.multi_cell(0, 5.5, edu.school, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(*pdf.muted_color)
            pdf.cell(0, 5.5, f"{edu.start_date} - {edu.end_date or 'Halen'}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*pdf.text_color_val)

    if profile.skills:
        pdf.section_title("Yetenekler")
        for group in profile.skills:
            pdf.set_font(FONT_FAMILY, "B", 9.5)
            pdf.set_text_color(*pdf.text_color_val)
            pdf.write(5.5, f"{group.category}: ")
            pdf.set_font(FONT_FAMILY, "", 9.5)
            pdf.set_text_color(*pdf.muted_color)
            pdf.write(5.5, ", ".join(group.items))
            pdf.ln(6.5)
            pdf.set_text_color(*pdf.text_color_val)

    if profile.projects:
        pdf.section_title("Projeler")
        for proj in profile.projects:
            pdf.set_font(FONT_FAMILY, "B", 10)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.multi_cell(0, 5.5, proj.name, new_x="LMARGIN", new_y="NEXT")
            if proj.description:
                pdf.set_font(FONT_FAMILY, "", 9)
                pdf.set_text_color(*TEXT_COLOR)
                pdf.multi_cell(0, 5, proj.description, new_x="LMARGIN", new_y="NEXT")
            if proj.technologies:
                pdf.set_font(FONT_FAMILY, "", 8.5)
                pdf.set_text_color(*MUTED_COLOR)
                pdf.multi_cell(0, 4.5, "Teknolojiler: " + ", ".join(proj.technologies), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    if profile.certifications:
        pdf.section_title("Sertifikalar")
        for cert in profile.certifications:
            pdf.set_font(FONT_FAMILY, "", 9.5)
            pdf.set_text_color(*TEXT_COLOR)
            pdf.set_x(pdf.l_margin)
            pdf.cell(4, 5, "-", new_x="RIGHT", new_y="TOP")
            pdf.multi_cell(0, 5, cert, new_x="LMARGIN", new_y="NEXT")

    if profile.languages:
        pdf.section_title("Diller")
        pdf.set_font(FONT_FAMILY, "", 9.5)
        pdf.multi_cell(0, 5.5, ", ".join(profile.languages), new_x="LMARGIN", new_y="NEXT")

    return pdf



def generate_cv(profile_path: Path, output_path: Path, theme: str = "classic_navy") -> None:
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = Profile.model_validate(data)
    pdf = build_cv(profile, theme=theme)
    pdf.output(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Profil JSON dosyasından PDF CV üretir.")
    parser.add_argument("--profile", type=Path, required=True, help="Profil JSON dosyası yolu")
    parser.add_argument("--output", type=Path, default=Path("cv.pdf"), help="Çıktı PDF yolu")
    parser.add_argument(
        "--theme",
        choices=list(THEMES.keys()),
        default="classic_navy",
        help=f"CV renk teması: {', '.join(THEMES.keys())}",
    )
    args = parser.parse_args()

    generate_cv(args.profile, args.output, theme=args.theme)
    print(f"CV oluşturuldu ({args.theme}): {args.output}")



if __name__ == "__main__":
    main()
