"""Yan yana iş ilanı karşılaştırma motoru (Side-by-Side Job Comparator)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.matching import contains_keyword, extract_matching_keywords, split_keywords, turkish_lower
from app.models import Profile


@dataclass
class JobComparisonColumn:
    job_url: str
    title: str
    company: str
    location: str
    site: str
    status: str
    salary: str
    is_remote: str
    match_score: str
    matched_skills: List[str]
    missing_skills: List[str]
    date_posted: str


@dataclass
class JobComparisonResult:
    columns: List[JobComparisonColumn]
    common_skills: List[str]
    recommendation: str


def format_salary(min_amount: Optional[float], max_amount: Optional[float], currency: Optional[str], interval: Optional[str]) -> str:
    """Maaş verisini okunabilir bir dizeye çevirir."""
    curr = (currency or "").upper()
    inter = f"/{interval}" if interval else ""
    if min_amount is not None and max_amount is not None:
        if min_amount == max_amount:
            return f"{min_amount:,.0f} {curr} {inter}".strip()
        return f"{min_amount:,.0f} - {max_amount:,.0f} {curr} {inter}".strip()
    elif min_amount is not None:
        return f"Min. {min_amount:,.0f} {curr} {inter}".strip()
    elif max_amount is not None:
        return f"Maks. {max_amount:,.0f} {curr} {inter}".strip()
    return "Belirtilmemiş"


def compare_jobs(jobs: List[Dict[str, Any]], profile: Optional[Profile] = None) -> JobComparisonResult:
    """Verilen 2 veya daha fazla ilanı yan yana analiz eder ve karşılaştırır."""
    if not jobs:
        return JobComparisonResult(columns=[], common_skills=[], recommendation="Karşılaştırılacak ilan seçilmedi.")

    profile_skills: set[str] = set()
    if profile:
        for grp in profile.skills:
            for item in grp.items:
                item_str = item.strip()
                if item_str:
                    profile_skills.add(turkish_lower(item_str))
                    profile_skills.update(split_keywords(item_str))
        for exp in profile.experience:
            for item in exp.tech_stack:
                item_str = item.strip()
                if item_str:
                    profile_skills.add(turkish_lower(item_str))
                    profile_skills.update(split_keywords(item_str))

    columns: List[JobComparisonColumn] = []
    job_matched_sets: List[set[str]] = []

    for j in jobs:
        title = j.get("title") or "Belirtilmemiş"
        company = j.get("company") or "Belirtilmemiş"
        location = j.get("location") or "Belirtilmemiş"
        site = (j.get("site") or "").capitalize()
        status = (j.get("status") or "yeni").capitalize()
        date_posted = j.get("date_posted") or "Bilinmiyor"
        job_url = j.get("job_url") or ""

        # Maaş
        salary_str = format_salary(
            j.get("min_amount"),
            j.get("max_amount"),
            j.get("currency"),
            j.get("salary_interval"),
        )

        # Uzaktan çalışma
        is_rem_val = j.get("is_remote")
        if is_rem_val == 1 or is_rem_val is True:
            remote_str = "Evet (Uzaktan / Hibrit)"
        else:
            text = f"{title} {location} {j.get('description') or ''}".lower()
            if any(k in text for k in ("remote", "uzaktan", "evden", "hibrit", "hybrid")):
                remote_str = "Evet (Uzaktan / Hibrit)"
            else:
                remote_str = "Ofis / Yerinde"

        # Eşleşme skoru
        raw_score = j.get("match_score")
        if raw_score is not None:
            score_str = f"%{int(raw_score * 100)}"
        else:
            score_str = "—"

        # Yetenekler
        desc = f"{title}\n{j.get('description') or ''}"
        matched: List[str] = []
        missing: List[str] = []
        if profile_skills:
            matched = extract_matching_keywords(desc, profile_skills)
            matched_set = set(matched)
            job_matched_sets.append(matched_set)
            # Profilde olup bu ilanda eşleşmeyenler
            missing = sorted(list(profile_skills - matched_set))[:8]
        else:
            job_matched_sets.append(set())

        columns.append(
            JobComparisonColumn(
                job_url=job_url,
                title=title,
                company=company,
                location=location,
                site=site,
                status=status,
                salary=salary_str,
                is_remote=remote_str,
                match_score=score_str,
                matched_skills=matched,
                missing_skills=missing,
                date_posted=date_posted,
            )
        )

    # Ortak eşleşen yetenekler
    common_skills: List[str] = []
    if job_matched_sets and all(job_matched_sets):
        common = set.intersection(*job_matched_sets)
        common_skills = sorted(list(common))

    # En yüksek skorlu ilanı tespit et
    best_job = max(jobs, key=lambda x: (x.get("match_score") or 0.0))
    best_title = best_job.get("title", "")
    best_comp = best_job.get("company", "")
    best_score = int((best_job.get("match_score") or 0.0) * 100)

    if best_score > 0:
        recommendation = f"Profilinizle en yüksek uyuma sahip ilan: **{best_title} @ {best_comp}** (Uyum Skoru: %{best_score})."
    else:
        recommendation = f"İlanlar arasında belirgin bir skor farkı yok. Lokasyon ve çalışma modeline göre değerlendirebilirsiniz."

    return JobComparisonResult(
        columns=columns,
        common_skills=common_skills,
        recommendation=recommendation,
    )
