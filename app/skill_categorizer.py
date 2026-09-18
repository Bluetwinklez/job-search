"""Yetenek kategorizasyon ve akıllı gruplama motoru.

Kullanıcının dağınık veya tek liste halindeki yeteneklerini ATS standartlarında
Frontend, Backend, Veritabanı, Bulut & DevOps, Veri & AI, Mobil, Test ve Araçlar
kategorilerine ayırır. Ayrıca iş deneyimlerinden çıkarılabilecek yetenekleri önerir.
"""

from __future__ import annotations

from typing import Dict, List, Set
from app.models import Experience, Profile, SkillGroup

_SKILL_TAXONOMY: Dict[str, Set[str]] = {
    "Frontend": {
        "react", "react.js", "vue", "vue.js", "angular", "svelte", "typescript",
        "javascript", "html", "html5", "css", "css3", "sass", "scss", "tailwind",
        "tailwindcss", "bootstrap", "next.js", "nextjs", "nuxt", "nuxtjs",
        "redux", "zustand", "webpack", "vite", "graphql"
    },
    "Backend": {
        "python", "fastapi", "django", "flask", "node.js", "nodejs", "express",
        "express.js", "go", "golang", "java", "spring", "spring boot", "c#",
        ".net", "asp.net", "rust", "php", "laravel", "ruby", "ruby on rails",
        "c++", "c", "rest", "rest api", "grpc", "microservices", "celery"
    },
    "Veritabanı & Depolama": {
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
        "elasticsearch", "dynamodb", "cassandra", "mariadb", "oracle", "sql server",
        "neo4j", "supabase", "firebase", "sql"
    },
    "Bulut & DevOps": {
        "docker", "kubernetes", "k8s", "aws", "amazon web services", "gcp",
        "google cloud", "azure", "ci/cd", "github actions", "gitlab ci", "jenkins",
        "terraform", "ansible", "linux", "bash", "nginx", "prometheus", "grafana",
        "helm", "cloudformation"
    },
    "Veri & Yapay Zeka": {
        "pandas", "numpy", "scipy", "scikit-learn", "sklearn", "pytorch",
        "tensorflow", "keras", "bigquery", "airflow", "spark", "hadoop", "kafka",
        "dbt", "machine learning", "deep learning", "nlp", "llm", "opencv",
        "langchain", "data analysis", "veri analizi"
    },
    "Mobil": {
        "flutter", "react native", "swift", "swiftui", "kotlin", "ios", "android",
        "dart", "objective-c", "xamarin"
    },
    "Test & Kalite": {
        "pytest", "unittest", "jest", "cypress", "selenium", "postman",
        "playwright", "junit", "mockito", "sonarqube", "qa", "test otomasyonu"
    },
    "Araçlar & Metodoloji": {
        "git", "github", "gitlab", "jira", "confluence", "trello", "agile",
        "scrum", "kanban", "figma", "postman", "swagger", "openapi"
    },
}


def _normalize(name: str) -> str:
    return name.strip().lower()


def categorize_skills(skills: List[str]) -> List[SkillGroup]:
    """Verilen düz yetenek listesini kategorilere ayırarak SkillGroup listesi döner."""
    categorized: Dict[str, List[str]] = {cat: [] for cat in _SKILL_TAXONOMY}
    uncategorized: List[str] = []

    seen = set()
    for skill in skills:
        cleaned = skill.strip()
        if not cleaned:
            continue
        norm = _normalize(cleaned)
        if norm in seen:
            continue
        seen.add(norm)

        matched_cat = None
        for cat, kw_set in _SKILL_TAXONOMY.items():
            if norm in kw_set:
                matched_cat = cat
                break

        if matched_cat:
            categorized[matched_cat].append(cleaned)
        else:
            uncategorized.append(cleaned)

    result: List[SkillGroup] = []
    for cat, items in categorized.items():
        if items:
            result.append(SkillGroup(category=cat, items=sorted(items, key=lambda s: s.lower())))

    if uncategorized:
        result.append(SkillGroup(category="Diğer Yetenekler", items=sorted(uncategorized, key=lambda s: s.lower())))

    return result


def extract_skills_from_profile(profile: Profile) -> List[str]:
    """Profildeki iş deneyimlerinin tech_stack ve açıklamalarından yetenek adaylarını çıkarır."""
    found: Set[str] = set()

    for exp in profile.experience:
        for tech in exp.tech_stack:
            cleaned = tech.strip()
            if cleaned:
                found.add(cleaned)

    existing_skills = {
        _normalize(item)
        for sg in profile.skills
        for item in sg.items
    }

    new_suggestions = [s for s in sorted(found) if _normalize(s) not in existing_skills]
    return new_suggestions
