"""Profil form editörü için veri dönüştürme ve yardımcı araçlar."""

from __future__ import annotations

from typing import Any, Dict, List
from app.models import (
    ContactInfo,
    Education,
    Experience,
    Profile,
    Project,
    SkillGroup,
)


def parse_bullets(text: str) -> List[str]:
    """Her satırı veya tireyle başlayan maddeyi temiz bir listeye çevirir."""
    items = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            line = line[2:].strip()
        items.append(line)
    return items


def format_bullets(items: List[str]) -> str:
    """Madde işaretli listeyi her satır bir madde olacak metne çevirir."""
    return "\n".join(f"• {item}" if not item.startswith("• ") else item for item in items)


def parse_comma_list(text: str) -> List[str]:
    """Virgülle ayrılmış metni listeye çevirir."""
    return [item.strip() for item in text.split(",") if item.strip()]


def format_comma_list(items: List[str]) -> str:
    """Listeyi virgülle ayrılmış metne çevirir."""
    return ", ".join(items)


def create_blank_experience() -> Dict[str, Any]:
    return {
        "company": "",
        "role": "",
        "location": "",
        "start_date": "",
        "end_date": "",
        "highlights": "",
        "tech_stack": "",
    }


def create_blank_education() -> Dict[str, Any]:
    return {
        "school": "",
        "degree": "",
        "field": "",
        "start_date": "",
        "end_date": "",
    }


def create_blank_skill_group() -> Dict[str, Any]:
    return {
        "category": "Teknik Yetenekler",
        "items": "",
    }


def create_blank_project() -> Dict[str, Any]:
    return {
        "name": "",
        "description": "",
        "technologies": "",
        "url": "",
    }


def profile_to_form_dict(profile: Profile) -> Dict[str, Any]:
    """Profile nesnesini Form arayüzünde düzenlenebilir sözlüğe çevirir."""
    return {
        "contact": {
            "full_name": profile.contact.full_name or "",
            "title": profile.contact.title or "",
            "email": str(profile.contact.email) if profile.contact.email else "",
            "phone": profile.contact.phone or "",
            "location": profile.contact.location or "",
            "linkedin": profile.contact.linkedin or "",
            "github": profile.contact.github or "",
            "website": profile.contact.website or "",
        },
        "summary": profile.summary or "",
        "experience": [
            {
                "company": exp.company,
                "role": exp.role,
                "location": exp.location or "",
                "start_date": exp.start_date,
                "end_date": exp.end_date or "",
                "highlights": format_bullets(exp.highlights),
                "tech_stack": format_comma_list(exp.tech_stack),
            }
            for exp in profile.experience
        ],
        "education": [
            {
                "school": edu.school,
                "degree": edu.degree,
                "field": edu.field or "",
                "start_date": edu.start_date,
                "end_date": edu.end_date or "",
            }
            for edu in profile.education
        ],
        "skills": [
            {
                "category": sg.category,
                "items": format_comma_list(sg.items),
            }
            for sg in profile.skills
        ],
        "languages": format_comma_list(profile.languages),
        "certifications": format_comma_list(profile.certifications),
        "projects": [
            {
                "name": proj.name,
                "description": proj.description or "",
                "technologies": format_comma_list(proj.technologies),
                "url": proj.url or "",
            }
            for proj in profile.projects
        ],
    }


def form_dict_to_profile(data: Dict[str, Any]) -> Profile:
    """Formdan gelen ham sözlüğü pydantic Profile nesnesine dönüştürür ve doğrular."""
    contact_data = data.get("contact", {})
    contact = ContactInfo(
        full_name=contact_data.get("full_name", "").strip(),
        title=contact_data.get("title", "").strip(),
        email=contact_data.get("email", "").strip(),
        phone=contact_data.get("phone", "").strip() or None,
        location=contact_data.get("location", "").strip() or None,
        linkedin=contact_data.get("linkedin", "").strip() or None,
        github=contact_data.get("github", "").strip() or None,
        website=contact_data.get("website", "").strip() or None,
    )

    summary = data.get("summary", "").strip() or None

    experience = []
    for exp in data.get("experience", []):
        company = exp.get("company", "").strip()
        role = exp.get("role", "").strip()
        if not company and not role:
            continue
        experience.append(
            Experience(
                company=company,
                role=role,
                location=exp.get("location", "").strip() or None,
                start_date=exp.get("start_date", "").strip(),
                end_date=exp.get("end_date", "").strip() or None,
                highlights=parse_bullets(exp.get("highlights", "")),
                tech_stack=parse_comma_list(exp.get("tech_stack", "")),
            )
        )

    education = []
    for edu in data.get("education", []):
        school = edu.get("school", "").strip()
        degree = edu.get("degree", "").strip()
        if not school and not degree:
            continue
        education.append(
            Education(
                school=school,
                degree=degree,
                field=edu.get("field", "").strip() or None,
                start_date=edu.get("start_date", "").strip(),
                end_date=edu.get("end_date", "").strip() or None,
            )
        )

    skills = []
    for sg in data.get("skills", []):
        cat = sg.get("category", "").strip()
        items = parse_comma_list(sg.get("items", ""))
        if not cat and not items:
            continue
        skills.append(
            SkillGroup(
                category=cat or "Genel",
                items=items,
            )
        )

    languages = parse_comma_list(data.get("languages", ""))
    certifications = parse_comma_list(data.get("certifications", ""))

    projects = []
    for proj in data.get("projects", []):
        name = proj.get("name", "").strip()
        if not name:
            continue
        projects.append(
            Project(
                name=name,
                description=proj.get("description", "").strip() or None,
                technologies=parse_comma_list(proj.get("technologies", "")),
                url=proj.get("url", "").strip() or None,
            )
        )

    return Profile(
        contact=contact,
        summary=summary,
        experience=experience,
        education=education,
        skills=skills,
        languages=languages,
        certifications=certifications,
        projects=projects,
    )
