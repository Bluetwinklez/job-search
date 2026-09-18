"""Maaş beklentisi, piyasa bant analizi ve maaş pazarlığı koçu modülü."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.matching import turkish_lower


@dataclass
class SalaryEstimateResult:
    role: str
    experience_level: str
    location: str
    currency: str
    min_monthly: float
    median_monthly: float
    max_monthly: float
    min_annual: float
    max_annual: float
    market_insights: str
    negotiation_tips: List[str]
    talking_points: List[str]


# Türkiye ve Global piyasası için temel rol taban maaş katsayıları (TRY bazında aylık net/brüt referansı)
_ROLE_BASELINES: Dict[str, float] = {
    "backend": 75000,
    "frontend": 70000,
    "fullstack": 78000,
    "mobile": 75000,
    "ios": 78000,
    "android": 75000,
    "devops": 85000,
    "cloud": 85000,
    "data engineer": 82000,
    "veri mühendisi": 82000,
    "data scientist": 80000,
    "veri bilimci": 80000,
    "qa": 60000,
    "test": 60000,
    "product manager": 85000,
    "ürün yöneticisi": 85000,
    "ui/ux": 65000,
    "tasarım": 60000,
    "eczane": 40000,
    "teknisyen": 38000,
}

_EXP_MULTIPLIERS: Dict[str, tuple[float, float, float]] = {
    "junior": (0.6, 0.75, 0.9),       # 0-2 yıl
    "mid": (0.9, 1.15, 1.4),          # 2-5 yıl
    "senior": (1.35, 1.7, 2.2),       # 5-8 yıl
    "lead": (1.8, 2.3, 3.0),          # 8+ yıl
}

_LOCATION_MULTIPLIERS: Dict[str, float] = {
    "istanbul": 1.15,
    "ankara": 1.0,
    "izmir": 0.95,
    "remote": 1.20,
    "uzaktan": 1.20,
    "yurtdisi": 2.5,
    "global": 2.5,
}


def estimate_salary(
    role: str,
    experience_level: str = "mid",
    location: str = "istanbul",
    currency: str = "TRY",
) -> SalaryEstimateResult:
    """Verilen pozisyon, kıdem ve konuma göre piyasa maaş aralığını ve pazarlık argümanlarını üretir."""
    role_norm = turkish_lower(role)
    exp_norm = experience_level.lower()
    loc_norm = turkish_lower(location)

    # Rol taban maaşını bul
    base_salary = 60000.0  # Genel varsayılan
    for key, val in _ROLE_BASELINES.items():
        if key in role_norm:
            base_salary = val
            break

    # Deneyim çarpanını seç
    exp_key = "mid"
    for ek in _EXP_MULTIPLIERS:
        if ek in exp_norm:
            exp_key = ek
            break
    min_mul, med_mul, max_mul = _EXP_MULTIPLIERS[exp_key]

    # Konum çarpanı
    loc_mul = 1.0
    for lk, lm in _LOCATION_MULTIPLIERS.items():
        if lk in loc_norm:
            loc_mul = lm
            break

    min_monthly = round(base_salary * min_mul * loc_mul, -2)
    median_monthly = round(base_salary * med_mul * loc_mul, -2)
    max_monthly = round(base_salary * max_mul * loc_mul, -2)

    # Para birimi dönüştürme (yaklaşık kur)
    curr_upper = currency.upper()
    if curr_upper == "USD":
        min_monthly = round(min_monthly / 38, -1)
        median_monthly = round(median_monthly / 38, -1)
        max_monthly = round(max_monthly / 38, -1)
    elif curr_upper == "EUR":
        min_monthly = round(min_monthly / 42, -1)
        median_monthly = round(median_monthly / 42, -1)
        max_monthly = round(max_monthly / 42, -1)

    min_annual = min_monthly * 12
    max_annual = max_monthly * 12

    insights = (
        f"{role.title()} pozisyonu için {exp_key.capitalize()} seviyesinde "
        f"tahmini piyasa maaş bandı {min_monthly:,.0f} - {max_monthly:,.0f} {curr_upper} aralığındadır. "
        f"Şirketin büyüklüğü, sağlanan ek yan haklar ve teknik uzmanlık derinliğine göre teklifler değişkenlik gösterir."
    )

    negotiation_tips = [
        "Maaş beklentisi sorulduğunda tek bir rakam yerine aralık verin ve aralığın alt sınırını kabul edeceğiniz en düşük rakam yapın.",
        "Yalnızca temel maaşa odaklanmayın; prim, özel sağlık sigortası, yemek/yol kartı ve eğitim bütçesini de pakete dahil edin.",
        "Geçmiş projelerinizdeki somut metrikleri (ör. 'Gecikmeyi %40 düşürdüm', '2M istek yönettim') değer kanıtı olarak sunun.",
        "İlk teklifi hemen kabul etmeyin; 'Teklifiniz için teşekkürler, inceleyip 24 saat içinde dönüş yapacağım' diyerek düşünme payı bırakın.",
    ]

    talking_points = [
        f"Benim seviyemdeki ve {role.title()} rolündeki profesyoneller için sektör piyasa araştırmam {min_monthly:,.0f} - {max_monthly:,.0f} {curr_upper} bandına işaret ediyor.",
        "Önceki işlerimde teknik borcu azaltarak sistem verimliliğini somut oranda artırdım; ekibinize de benzer bir katma değer sağlayabilirim.",
        "Eğer bütçeniz bu aralığın altındaysa, esnek çalışma saatleri, uzaktan çalışma ödeneği veya 6. ayda performans bazlı revizyon opsiyonunu görüşebiliriz.",
    ]

    return SalaryEstimateResult(
        role=role,
        experience_level=exp_key,
        location=location,
        currency=curr_upper,
        min_monthly=min_monthly,
        median_monthly=median_monthly,
        max_monthly=max_monthly,
        min_annual=min_annual,
        max_annual=max_annual,
        market_insights=insights,
        negotiation_tips=negotiation_tips,
        talking_points=talking_points,
    )
