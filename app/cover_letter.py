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


def _latest_experience(profile: Profile) -> Experience | None:
    """Profildeki en güncel (halen devam eden veya en yeni biten) deneyimi döner."""
    if not profile.experience:
        return None
    for exp in profile.experience:
        if exp.end_date is None:
            return exp
    try:
        return max(profile.experience, key=lambda e: (e.end_date or "", e.start_date or ""))
    except Exception:
        return profile.experience[0]


def _most_relevant_experience(profile: Profile, job_title: str, job_description: str | None) -> Experience | None:
    if not profile.experience:
        return None
    latest_fallback = _latest_experience(profile)
    job_words = split_keywords(f"{job_title} {job_description or ''}")
    if not job_words:
        return latest_fallback

    best_exp = latest_fallback
    best_score = -1
    for exp in profile.experience:
        exp_text = f"{exp.company} {exp.role} {' '.join(exp.highlights)} {' '.join(exp.tech_stack)}"
        exp_words = split_keywords(exp_text)
        score = sum(1 for w in exp_words if w in job_words)
        if score > best_score:
            best_score = score
            best_exp = exp
    return best_exp if best_score > 0 else latest_fallback



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


def generate_cover_letter_english(
    profile: Profile,
    job_title: str,
    company: str,
    job_description: str | None = None,
    provider: str = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    """İngilizce ön yazı taslağı üretir (LLM ile).

    Önce Türkçe şablon taslağı üretilir, ardından yapay zeka yalnızca bu metni
    doğal İngilizceye çevirir/uyarlar — yeni bir deneyim veya başarı uydurmaz.
    """
    from app.llm_client import generate_llm_response

    turkish_draft = generate_cover_letter(profile, job_title, company, job_description)

    system_prompt = (
        "You are a professional English cover-letter writer. You will be given a Turkish "
        "cover letter draft. Rewrite it in natural, professional English, preserving every "
        "fact exactly as given (company name, job title, technologies, achievements, contact "
        "info). Do NOT invent, add, or embellish any experience, skill, or fact that is not "
        "already present in the draft. Return only the final English letter text, no preamble."
    )
    prompt = f"Turkish cover letter draft:\n\n{turkish_draft}\n\nRewrite this in English."

    return generate_llm_response(
        prompt,
        system_prompt=system_prompt,
        provider=provider,
        model=model,
        api_key=api_key,
    ).strip()


def generate_bulk_cover_letters(
    profile: Profile,
    jobs: list[dict],
    language: str = "tr",
    provider: str = "anthropic",
    model: str | None = None,
    api_key: str | None = None,
) -> dict[str, str]:
    """Birden fazla ilan için tek seferde ön yazı taslağı üretir.

    Döner: {job_url: ön_yazı_metni}
    """
    letters: dict[str, str] = {}
    for job in jobs:
        job_url = job.get("job_url") or job.get("title", "")
        title = job.get("title") or ""
        company = job.get("company") or ""
        description = job.get("description")
        if language == "en":
            letters[job_url] = generate_cover_letter_english(
                profile, title, company, description, provider=provider, model=model, api_key=api_key
            )
        else:
            letters[job_url] = generate_cover_letter(profile, title, company, description)
    return letters


def render_letter_pdf(
    letter_text: str,
    profile: Profile | None = None,
    theme: str = "classic_navy",
):
    """Düz metin ön yazıyı, kurumsal antet ve CV temasıyla uyumlu profesyonel bir PDF'e dönüştürür."""
    from datetime import date
    from fpdf import FPDF
    from app.cv_generator import FONT_FAMILY, FONTS_DIR, THEMES

    theme_data = THEMES.get(theme, THEMES["classic_navy"])
    primary_color = theme_data.get("accent", (28, 56, 111))

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_font(FONT_FAMILY, "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font(FONT_FAMILY, "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # Kurumsal Antet (Eğer profile verilmişse)
    if profile:
        # İsim
        pdf.set_font(FONT_FAMILY, "B", 18)
        pdf.set_text_color(*primary_color)
        pdf.cell(0, 8, profile.contact.full_name, new_x="LMARGIN", new_y="NEXT")

        # Ünvan
        pdf.set_font(FONT_FAMILY, "", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, profile.contact.title, new_x="LMARGIN", new_y="NEXT")

        # İletişim satırı
        contact_parts = [profile.contact.email]
        if profile.contact.phone:
            contact_parts.append(profile.contact.phone)
        if profile.contact.location:
            contact_parts.append(profile.contact.location)
        if profile.contact.linkedin:
            contact_parts.append(profile.contact.linkedin)

        pdf.set_font(FONT_FAMILY, "", 9)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(0, 5, "  •  ".join(contact_parts), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

        # Kurumsal renkli ayırıcı çizgi
        pdf.set_draw_color(*primary_color)
        pdf.set_line_width(0.8)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y())
        pdf.ln(6)

        # Tarih
        pdf.set_font(FONT_FAMILY, "", 10)
        pdf.set_text_color(120, 120, 120)
        today_str = date.today().strftime("%d.%m.%Y")
        pdf.cell(0, 5, f"Tarih: {today_str}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Metin Gövdesi
    pdf.set_font(FONT_FAMILY, "", 10.5)
    pdf.set_text_color(40, 40, 40)
    for line in letter_text.split("\n"):
        if line.strip() == "":
            pdf.ln(3.5)
        else:
            pdf.multi_cell(0, 5.5, line, new_x="LMARGIN", new_y="NEXT")

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
