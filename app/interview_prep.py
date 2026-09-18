"""İlana ve adayın profiline özel mülakat hazırlık asistanı."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from app.matching import extract_matching_keywords
from app.models import Profile

DEFAULT_MODEL = "claude-3-7-sonnet-20250219"


class InterviewQuestion(BaseModel):
    category: str = Field(description="Soru kategorisi: 'Teknik/Rol Odaklı', 'Davranışsal (STAR)', veya 'İşverene Sorulacak Soru'")
    question: str = Field(description="Mülakatta sorulabilecek soru")
    rationale: str = Field(description="İşverenin bu soruyu sorma amacı ve aradığı sinyal")
    answer_tip: str = Field(description="Adayın profilindeki hangi deneyimi/yetenekleri referans vererek cevaplaması gerektiği")


class InterviewPrepResult(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)
    key_strengths: list[str] = Field(description="Adayın bu ilan için öne çıkarması gereken 3 temel güçlü yönü")
    potential_gaps: list[str] = Field(description="Adayın mülakatta savunması veya açıklaması gerekebilecek 2 olası eksik/zayıf nokta")


def generate_baseline_interview_prep(
    profile: Profile,
    job_title: str,
    company: str,
    job_description: str | None = None,
) -> InterviewPrepResult:
    """LLM API anahtarı olmadığında profil ve ilandan kural tabanlı mülakat rehberi üretir."""
    all_skills = [item for group in profile.skills for item in group.items]
    matched = extract_matching_keywords(job_description or "", all_skills) if job_description else all_skills[:3]
    latest = profile.experience[0] if profile.experience else None
    latest_company = latest.company if latest else "önceki çalışmalarınız"

    questions = [
        InterviewQuestion(
            category="Teknik/Rol Odaklı",
            question=f"{job_title} pozisyonunda karşılaştığınız en zorlu teknik veya operasyonel problemi nasıl çözdünüz?",
            rationale="Problem çözme yeteneğinizi, analitik düşünme yapınızı ve kriz anındaki karar alma sürecinizi anlamak isterler.",
            answer_tip=f"{latest_company} bünyesindeki deneyiminizi ve {', '.join(matched[:2]) if matched else 'uzmanlık alanınızı'} somut sonuçlarla aktarın.",
        ),
        InterviewQuestion(
            category="Teknik/Rol Odaklı",
            question=f"{company} için kritik olan {matched[0] if matched else job_title} konusunda bugüne kadarki en büyük başarınız nedir?",
            rationale="Pozisyonun temel gereksinimlerindeki yetkinlik seviyenizi ölçmek.",
            answer_tip="Sayısal veriler (% verimlilik, süre kısalması vb.) vererek somut bir başarı hikayesi anlatın.",
        ),
        InterviewQuestion(
            category="Davranışsal (STAR)",
            question="Ekip içinde bir anlaşmazlık veya fikir ayrılığı yaşadığınız bir anı ve bunu nasıl çözdüğünüzü paylaşır mısınız?",
            rationale="İletişim becerisi, çatışma yönetimi ve takım çalışmasına yatkınlık.",
            answer_tip="Durum (Situation), Görev (Task), Eylem (Action) ve Sonuç (Result) metodunu kullanarak profesyonel yaklaşımınızı vurgulayın.",
        ),
        InterviewQuestion(
            category="İşverene Sorulacak Soru",
            question=f"{job_title} rolünde ilk 3 ayda başarılı sayılmam için ulaşmam gereken en önemli hedef nedir?",
            rationale="Hedef odaklı, proaktif ve şirkete hızlı değer katmaya hazır bir aday profili çizer.",
            answer_tip="Mülakat sonunda 'Bize sormak istediğiniz bir şey var mı?' dendiğinde bu soruyu yöneltin.",
        ),
        InterviewQuestion(
            category="İşverene Sorulacak Soru",
            question=f"{company} ekibinin önümüzdeki dönemde çözmeyi hedeflediği en büyük öncelik veya vizyon nedir?",
            rationale="Şirketin geleceğini ve uzun vadeli stratejisini önemsediğinizi gösterir.",
            answer_tip="Şirket dinamiklerini anlamak ve kültürel uyumu değerlendirmek için harika bir sorudur.",
        ),
    ]

    return InterviewPrepResult(
        questions=questions,
        key_strengths=[
            f"{latest.role if latest else 'Deneyim'}: {latest_company} tecrübesi",
            f"Yetkinlikler: {', '.join(matched[:3]) if matched else 'Geniş yetenek seti'}",
            f"{company} bünyesindeki {job_title} hedefleriyle örtüşen arka plan",
        ],
        potential_gaps=[
            "İlan açıklamasında geçen şirket içi özel iş akışlarına hızlı adaptasyon sağlama",
            "Mülakat sırasında teorik değil doğrudan yaşanmış vaka örneklerine odaklanma",
        ],
    )


def generate_mock_interview(
    profile: Profile,
    job_title: str,
    company: str,
    job_description: str | None = None,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> InterviewPrepResult:
    """Claude API ile veya kural tabanlı olarak mülakat hazırlık seti üretir."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return generate_baseline_interview_prep(profile, job_title, company, job_description)

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=key)
        parse_fn = getattr(client.beta.messages, "parse", None) if hasattr(client, "beta") else None
        if parse_fn is None:
            parse_fn = getattr(client.messages, "parse", None)

        if parse_fn is None:
            return generate_baseline_interview_prep(profile, job_title, company, job_description)

        prompt = f"""
        Bir aday aşağıdaki pozisyona mülakata girecektir.

        ŞİRKET: {company}
        POZİSYON: {job_title}
        İLAN AÇIKLAMASI:
        {job_description or 'Belirtilmedi'}

        ADAYIN PROFİLİ:
        {json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)}

        Görevin: Bu adayı mülakata en iyi şekilde hazırlayacak soruları ve stratejiyi oluşturmak.
        Adayın kendi geçmişindeki gerçekleri (şirketleri, projeleri, yetenekleri) referans alarak cevap ipuçları ver.
        """

        response = parse_fn(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            output_format=InterviewPrepResult,
        )
        return response.parsed_output
    except Exception:
        # API çağrısı başarısız olursa kural tabanlı zengin çıktıyı döndür
        return generate_baseline_interview_prep(profile, job_title, company, job_description)
