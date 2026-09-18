"""İlana özel CV uyarlama (Claude API ile).

Claude'a profilin tamamını göndermek ve onun serbestçe yeni cümleler
uydurmasına izin vermek yerine, model yalnızca iki şeye karar verir:
  1. İlana özel, profildeki gerçeklere dayanan kısa bir özet metni.
  2. Mevcut deneyim maddelerinin/teknolojilerinin/yeteneklerin, ilanla
     alaka düzeyine göre yeniden sıralanması (indeks listesi olarak).

Böylece CV'deki deneyim/yetenek gerçekleri asla model tarafından
"uydurulmaz" — yalnızca hangilerinin öne çıkarılacağı seçilir. Sonuç,
mevcut `app.cv_generator.build_cv` ile aynı şekilde PDF'e dönüştürülür.

Kullanım:
    python -m app.cv_tailor --profile data/profile.json \\
        --job-description-file ilan.txt --output cv_tailored.pdf

ANTHROPIC_API_KEY ortam değişkeninin (veya `ant auth login` ile
kaydedilmiş bir profilin) tanımlı olması gerekir.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import BaseModel, Field

from app.models import Experience, Profile, SkillGroup

DEFAULT_MODEL = "claude-opus-5"


class TailoredExperience(BaseModel):
    highlight_order: list[int] = Field(
        description="Orijinal highlights listesindeki indeksler (0 tabanlı), ilanla "
        "alaka düzeyine göre en alakalıdan en az alakalıya sıralanmış. Alakasız "
        "olanlar çıkarılabilir ama en az bir tane kalmalı."
    )
    tech_stack_order: list[int] = Field(
        default_factory=list,
        description="Orijinal tech_stack listesindeki indeksler, en alakalı önce olacak şekilde sıralanmış.",
    )


class TailoredSkillGroup(BaseModel):
    category: str
    item_order: list[int] = Field(description="Orijinal items listesindeki indeksler, en alakalı önce.")


class TailoringResult(BaseModel):
    summary: str = Field(
        description="Bu ilana özel, 2-4 cümlelik CV özeti. Yalnızca adayın profilinde zaten var olan "
        "gerçekleri kullan, yeni deneyim/yetenek uydurma."
    )
    experience: list[TailoredExperience] = Field(
        description="Profildeki deneyim listesiyle AYNI SIRADA, aynı sayıda eleman içermeli."
    )
    skills: list[TailoredSkillGroup] = Field(default_factory=list)
    missing_keywords: list[str] = Field(
        default_factory=list,
        description="İlanda geçen ama adayın profilinde hiç yer almayan önemli anahtar kelimeler/yetenekler.",
    )


def _build_prompt(profile: Profile, job_description: str) -> str:
    profile_view = {
        "summary": profile.summary,
        "experience": [
            {
                "company": exp.company,
                "role": exp.role,
                "highlights": {i: h for i, h in enumerate(exp.highlights)},
                "tech_stack": {i: t for i, t in enumerate(exp.tech_stack)},
            }
            for exp in profile.experience
        ],
        "skills": [
            {"category": g.category, "items": {i: it for i, it in enumerate(g.items)}} for g in profile.skills
        ],
    }
    return (
        "Aşağıda bir adayın CV profili (deneyim maddeleri ve yetenekler indeksli sözlükler "
        "olarak verilmiştir) ve başvurduğu iş ilanının açıklaması var.\n\n"
        f"PROFİL:\n{json.dumps(profile_view, ensure_ascii=False, indent=2)}\n\n"
        f"İLAN AÇIKLAMASI:\n{job_description}\n\n"
        "Görevin: bu ilana en uygun CV sunumunu belirlemek. Yeni deneyim, yetenek ya da "
        "başarı UYDURMA — yalnızca var olanlar arasından en alakalılarını seç ve öne çıkar. "
        "'experience' alanı profildeki deneyim listesiyle birebir aynı sırada ve aynı "
        "uzunlukta olmalı (her deneyim için bir TailoredExperience)."
    )


def tailor_profile(
    profile: Profile, job_description: str, model: str = DEFAULT_MODEL, api_key: str | None = None
) -> tuple[Profile, TailoringResult]:
    """Profili ilana göre uyarlar; (uyarlanmış profil, ham model çıktısı) döner."""
    import os

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY ortam değişkeni tanımlı değil. Lütfen geçerli bir Anthropic API anahtarı sağlayın."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    parse_fn = getattr(client.beta.messages, "parse", None) if hasattr(client, "beta") else None
    if parse_fn is None:
        parse_fn = getattr(client.messages, "parse", None)
    if parse_fn is None:
        raise RuntimeError("Yüklü anthropic kütüphanesi structured output (.parse) desteklemiyor. Lütfen güncelleyin.")

    response = parse_fn(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": _build_prompt(profile, job_description)}],
        output_format=TailoringResult,
    )
    result = response.parsed_output
    return _apply_tailoring(profile, result), result



def _reorder(items: list, order: list[int]) -> list:
    """`order` indekslerine göre `items`i yeniden sıralar; geçersiz/eksik girdilerde orijinali korur."""
    seen: set[int] = set()
    picked = []
    for i in order:
        if isinstance(i, int) and 0 <= i < len(items) and i not in seen:
            picked.append(items[i])
            seen.add(i)
    if not picked:
        return list(items)
    return picked


def _apply_tailoring(profile: Profile, result: TailoringResult) -> Profile:
    new_experience = []
    for i, exp in enumerate(profile.experience):
        if i < len(result.experience):
            tailored = result.experience[i]
            highlights = _reorder(exp.highlights, tailored.highlight_order)
            tech_stack = _reorder(exp.tech_stack, tailored.tech_stack_order) if exp.tech_stack else exp.tech_stack
        else:
            highlights, tech_stack = exp.highlights, exp.tech_stack
        new_experience.append(
            Experience(
                company=exp.company,
                role=exp.role,
                start_date=exp.start_date,
                end_date=exp.end_date,
                location=exp.location,
                highlights=highlights,
                tech_stack=tech_stack,
            )
        )

    tailored_skills_by_category = {g.category: g for g in result.skills}
    new_skills = []
    for group in profile.skills:
        tailored_group = tailored_skills_by_category.get(group.category)
        items = _reorder(group.items, tailored_group.item_order) if tailored_group else group.items
        new_skills.append(SkillGroup(category=group.category, items=items))

    return Profile(
        contact=profile.contact,
        summary=result.summary or profile.summary,
        experience=new_experience,
        education=profile.education,
        skills=new_skills,
        languages=profile.languages,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Profili bir iş ilanına göre uyarlayıp ATS-dostu PDF CV üretir.")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--job-description-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("cv_tailored.pdf"))
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Kullanılacak Claude modeli")
    args = parser.parse_args()

    from app.cv_generator import build_cv

    profile = Profile.model_validate(json.loads(args.profile.read_text(encoding="utf-8")))
    job_description = args.job_description_file.read_text(encoding="utf-8")

    tailored_profile, result = tailor_profile(profile, job_description, args.model)
    pdf = build_cv(tailored_profile)
    pdf.output(str(args.output))

    print(f"Uyarlanmış CV oluşturuldu: {args.output}")
    if result.missing_keywords:
        print("İlanda geçip profilde bulunmayan anahtar kelimeler:")
        for kw in result.missing_keywords:
            print(f"  - {kw}")


if __name__ == "__main__":
    main()
