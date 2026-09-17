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
import re
from pathlib import Path

from app.models import Profile


def _matching_skills(profile: Profile, job_description: str | None, top_n: int = 5) -> list[str]:
    all_skills = [item for group in profile.skills for item in group.items]
    if not job_description:
        return all_skills[:top_n]
    text = job_description.lower()
    matched = [s for s in all_skills if re.search(rf"(?<!\w){re.escape(s.lower())}(?!\w)", text)]
    ordered = matched + [s for s in all_skills if s not in matched]
    return ordered[:top_n]


def generate_cover_letter(
    profile: Profile,
    job_title: str,
    company: str,
    job_description: str | None = None,
) -> str:
    skills = _matching_skills(profile, job_description)
    skills_line = ", ".join(skills) if skills else ""

    latest_role = profile.experience[0] if profile.experience else None
    experience_line = ""
    if latest_role:
        experience_line = (
            f"Halihazırda {latest_role.company} bünyesinde {latest_role.role} olarak çalışıyor, "
            f"{', '.join(latest_role.tech_stack[:4])} gibi teknolojilerle üretim ortamına yönelik "
            f"projeler geliştiriyorum."
            if latest_role.tech_stack
            else f"Halihazırda {latest_role.company} bünyesinde {latest_role.role} olarak çalışıyorum."
        )

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


def main() -> None:
    parser = argparse.ArgumentParser(description="İlana özel ön yazı taslağı üretir.")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--title", required=True, help="İlanın pozisyon adı")
    parser.add_argument("--company", required=True, help="Şirket adı")
    parser.add_argument("--job-description-file", type=Path, default=None, help="İlan açıklaması (metin dosyası)")
    parser.add_argument("--output", type=Path, default=None, help="Çıktı dosyası (verilmezse ekrana yazdırılır)")
    args = parser.parse_args()

    profile = Profile.model_validate(json.loads(args.profile.read_text(encoding="utf-8")))
    job_description = args.job_description_file.read_text(encoding="utf-8") if args.job_description_file else None

    letter = generate_cover_letter(profile, args.title, args.company, job_description)
    if args.output:
        args.output.write_text(letter, encoding="utf-8")
        print(f"Ön yazı oluşturuldu: {args.output}")
    else:
        print(letter)


if __name__ == "__main__":
    main()
