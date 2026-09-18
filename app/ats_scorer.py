"""ATS (Başvuru Takip Sistemi) uyumluluk denetleyicisi ve skorlama motoru."""

from __future__ import annotations

import re
from pydantic import BaseModel, Field

from app.models import Profile


class ATSScoreBreakdown(BaseModel):
    contact_score: int = Field(description="İletişim bilgileri puanı (maks 15)")
    summary_score: int = Field(description="Özet metin puanı (maks 15)")
    experience_score: int = Field(description="Deneyim ve etki puanı (maks 30)")
    skills_score: int = Field(description="Yetenekler ve kategorizasyon puanı (maks 25)")
    education_score: int = Field(description="Eğitim bilgisi puanı (maks 15)")


class ATSAnalysisReport(BaseModel):
    total_score: int = Field(description="100 üzerinden toplam ATS puanı")
    breakdown: ATSScoreBreakdown
    strengths: list[str] = Field(description="Profilin ATS açısından güçlü yönleri")
    recommendations: list[str] = Field(description="Skoru artıracak somut tavsiyeler")
    metric_mentions_count: int = Field(description="Deneyimlerde geçen sayısal/ölçülebilir başarı sayısı")


_ACTION_VERBS = {
    "yönetti", "geliştirdi", "azalttı", "artırdı", "kurdu", "tasarladı", "sağladı",
    "optimize", "otomatize", "liderlik", "koordine", "entegre", "yürüttü", "başardı",
    "managed", "developed", "reduced", "increased", "built", "designed", "optimized",
}


def score_profile(profile: Profile) -> ATSAnalysisReport:
    """Verilen profili ATS sistemlerinin ayrıştırma kriterlerine göre puanlar."""
    strengths: list[str] = []
    recommendations: list[str] = []

    # 1. İletişim (15 puan)
    contact_pts = 0
    if profile.contact.full_name.strip():
        contact_pts += 3
    if profile.contact.title.strip():
        contact_pts += 3
    if profile.contact.email:
        contact_pts += 3
    if profile.contact.phone:
        contact_pts += 2
    if profile.contact.location:
        contact_pts += 2
    if profile.contact.linkedin or profile.contact.github:
        contact_pts += 2

    if contact_pts >= 13:
        strengths.append("İletişim bilgileri ve profesyonel ağ bağlantıları eksiksiz.")
    else:
        recommendations.append("İletişim bölümüne telefon, konum ve LinkedIn profil linki ekleyerek ATS ayrıştırmasını güçlendirin.")

    # 2. Özet (15 puan)
    summary_pts = 0
    if profile.summary:
        word_count = len(profile.summary.split())
        if 20 <= word_count <= 80:
            summary_pts = 15
            strengths.append(f"Özet metin ideal uzunlukta ({word_count} kelime) ve net bir uzmanlık alanı tanımlıyor.")
        elif word_count < 20:
            summary_pts = 8
            recommendations.append("Özet bölümü biraz kısa; uzmanlık alanınızı ve temel değer önerinizi 2-3 cümleyle genişletin.")
        else:
            summary_pts = 10
            recommendations.append("Özet bölümü biraz uzun; ATS taraması için 3-4 cümlede öz ve vurucu tutmanız önerilir.")
    else:
        recommendations.append("Özet (Summary) bölümü ekleyin. ATS sistemleri başlık altındaki özet metnini yüksek ağırlıkla tarar.")

    # 3. Deneyim (30 puan)
    exp_pts = 0
    metric_count = 0
    action_verb_count = 0

    if profile.experience:
        exp_pts += 10
        total_highlights = sum(len(e.highlights) for e in profile.experience)
        if total_highlights >= 3:
            exp_pts += 5

        # Sayısal metrik ve aksiyon fiilleri kontrolü
        for exp in profile.experience:
            for hl in exp.highlights:
                # Sayı, yüzde veya çarpan içeriyor mu? (%40, 2M, 5 kişilik, 3x)
                if re.search(r"(\b\d+(\.\d+)?%|\b\d+\+?|\b[0-9]+[MKk]\b)", hl):
                    metric_count += 1
                hl_lower = hl.lower()
                if any(v in hl_lower for v in _ACTION_VERBS):
                    action_verb_count += 1

        if metric_count >= 2:
            exp_pts += 8
            strengths.append(f"Deneyimlerde somut/ölçülebilir veriler ({metric_count} adet) kullanılmış; bu işveren etkisini %50 artırır.")
        else:
            recommendations.append("Deneyim maddelerine ölçülebilir sonuçlar ekleyin (ör. '%30 hızlandırdı', '5 kişilik ekibi yönetti').")

        if action_verb_count >= 2:
            exp_pts += 7
        else:
            recommendations.append("Pasif fiiller yerine güçlü aksiyon fiilleri ('yönetti', 'tasarladı', 'optimize etti') kullanın.")
    else:
        recommendations.append("En az bir iş veya staj deneyimi ekleyin.")

    # 4. Yetenekler (25 puan)
    skills_pts = 0
    all_skills = [item for g in profile.skills for item in g.items]
    if len(all_skills) >= 8:
        skills_pts += 15
        strengths.append(f"Zengin yetenek havuzu ({len(all_skills)} yetenek) ATS anahtar kelime eşleşmelerini kolaylaştırır.")
    elif len(all_skills) >= 4:
        skills_pts += 10
        recommendations.append("Yetenek listenizi genişleterek en az 8-10 temel teknoloji veya uzmanlık kelimesi ekleyin.")
    else:
        skills_pts += 5
        recommendations.append("Yetenek bölümü çok kısıtlı; sektörel araç ve yazılımları kategorize ederek ekleyin.")

    if len(profile.skills) >= 2:
        skills_pts += 10
    else:
        recommendations.append("Yeteneklerinizi mantıklı kategorilere ayırın (ör. 'Diller', 'Araçlar', 'Uzmanlıklar').")

    # 5. Eğitim & Sertifikalar (15 puan)
    edu_pts = 0
    if profile.education:
        edu_pts += 10
        strengths.append("Eğitim bilgisi şemaya uygun şekilde tanımlanmış.")
    else:
        recommendations.append("Eğitim bilgisi ekleyin.")

    if profile.certifications:
        edu_pts += 5
        strengths.append(f"Sertifikalar ({len(profile.certifications)} adet) teknik yetkinliğinizi onaylar nitelikte.")
    else:
        recommendations.append("Varsa mesleki sertifikalarınızı profilinize ekleyin.")

    breakdown = ATSScoreBreakdown(
        contact_score=min(contact_pts, 15),
        summary_score=min(summary_pts, 15),
        experience_score=min(exp_pts, 30),
        skills_score=min(skills_pts, 25),
        education_score=min(edu_pts, 15),
    )
    total_score = (
        breakdown.contact_score
        + breakdown.summary_score
        + breakdown.experience_score
        + breakdown.skills_score
        + breakdown.education_score
    )

    return ATSAnalysisReport(
        total_score=total_score,
        breakdown=breakdown,
        strengths=strengths,
        recommendations=recommendations,
        metric_mentions_count=metric_count,
    )
