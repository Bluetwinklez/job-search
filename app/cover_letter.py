"""İlana özel ön yazı (cover letter) taslağı üretimi.

LLM gerektirmez: profildeki özet, en güncel deneyim ve ilan açıklamasıyla
eşleşen yetenekleri birleştirip düzenlenebilir bir taslak metin üretir.

Kullanım:
    python -m app.cover_letter --profile data/profile.json \\
        --title "Backend Developer" --company "Acme" \\
        --job-description-file ilan.txt --output cover_letter.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.matching import contains_keyword, split_keywords
from app.models import Experience, Profile


def _matching_skills(profile: Profile, job_description: str | None, top_n: int = 5) -> list[str]:
    all_skills = [item for group in profile.skills for item in group.items]
    if not job_description:
        return all_skills[:top_n]
    matched = [s for s in all_skills if contains_keyword(job_description, s)]
    ordered = matched + [s for s in all_skills if s not in matched]
    return ordered[:top_n]


def _most_relevant_experience(profile: Profile, job_title: str, job_description: str | None) -> Experience | None:
    if not profile.experience:
        return None
    job_words = split_keywords(f"{job_title} {job_description or ''}")
    if not job_words:
        return profile.experience[0]

    best_exp = profile.experience[0]
    best_score = -1
    for exp in profile.experience:
        exp_text = f"{exp.company} {exp.role} {' '.join(exp.highlights)} {' '.join(exp.tech_stack)}"
        exp_words = split_keywords(exp_text)
        score = sum(1 for w in exp_words if w in job_words)
        if score > best_score:
            best_score = score
            best_exp = exp
    return best_exp if best_score > 0 else profile.experience[0]


def generate_cover_letter(
    profile: Profile,
    job_title: str,
    company: str,
    job_description: str | None = None,
) -> str:
    skills = _matching_skills(profile, job_description)
    skills_line = ", ".join(skills) if skills else ""

    latest_role = _most_relevant_experience(profile, job_title, job_description)
    experience_line = ""
    if latest_role:
        is_current = latest_role.end_date is None
        lead_in = (
            f"Halihazırda {latest_role.company} bünyesinde {latest_role.role} olarak çalışıyorum"
            if is_current
            else f"{latest_role.company} bünyesinde {latest_role.role} olarak çalıştım"
        )
        if latest_role.tech_stack:
            verb = "geliştiriyorum" if is_current else "geliştirdim"
            experience_line = (
                f"{lead_in}; {', '.join(latest_role.tech_stack[:4])} gibi teknolojilerle üretim "
                f"ortamına yönelik projeler {verb}."
            )
        else:
            experience_line = f"{lead_in}."

    highlight = ""
    if latest_role and latest_role.highlights:
        highlight = latest_role.highlights[0]

    paragraphs = [
        f"Sayın Yetkili,",
        "",
        f"{company} bünyesindeki {job_title} pozisyonu için başvurumu iletiyorum. "
        f"{profile.summary or ''}".strip(),
        "",
        experience_line,
        f"Bu süreçte {highlight}" if highlight else "",
        "",
        f"{skills_line + ' konularındaki deneyimimin' if skills_line else 'Deneyimimin'} "
        f"{company} ekibine kısa sürede katkı sağlayacağına inanıyorum. Pozisyonla ilgili "
        f"detayları görüşmek üzere sizinle bir araya gelmekten memnuniyet duyarım.",
        "",
        "Saygılarımla,",
        profile.contact.full_name,
        profile.contact.email,
    ]
    return "\n".join(p for p in paragraphs if p is not None)


def render_letter_pdf(letter_text: str):
    """Düz metin ön yazıyı, CV ile aynı yazı tipini kullanan bir PDF'e dönüştürür."""
    from fpdf import FPDF

    from app.cv_generator import FONT_FAMILY, FONTS_DIR

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font(FONT_FAMILY, "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_font(FONT_FAMILY, "", 11)
    for line in letter_text.split("\n"):
        if line.strip() == "":
            pdf.ln(4)
        else:
            pdf.multi_cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="İlana özel ön yazı taslağı üretir.")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--title", required=True, help="İlanın pozisyon adı")
    parser.add_argument("--company", required=True, help="Şirket adı")
    parser.add_argument("--job-description-file", type=Path, default=None, help="İlan açıklaması (metin dosyası)")
    parser.add_argument("--output", type=Path, default=None, help="Çıktı metin dosyası (verilmezse ekrana yazdırılır)")
    parser.add_argument("--pdf", type=Path, default=None, help="Verilirse, ön yazıyı PDF olarak da üretir")
    args = parser.parse_args()

    profile = Profile.model_validate(json.loads(args.profile.read_text(encoding="utf-8")))
    job_description = args.job_description_file.read_text(encoding="utf-8") if args.job_description_file else None

    letter = generate_cover_letter(profile, args.title, args.company, job_description)
    if args.output:
        args.output.write_text(letter, encoding="utf-8")
        print(f"Ön yazı oluşturuldu: {args.output}")
    else:
        print(letter)

    if args.pdf:
        render_letter_pdf(letter).output(str(args.pdf))
        print(f"PDF ön yazı oluşturuldu: {args.pdf}")


if __name__ == "__main__":
    main()
