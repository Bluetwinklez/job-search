"""Markdown formatında profesyonel CV oluşturucu.

Geliştiricilerin GitHub profillerinde (README.md), kişisel portfolyo sitelerinde
veya teknik bloglarında doğrudan kullanabilecekleri temiz GitHub-Flavored Markdown
çıktısı üretir.
"""

from __future__ import annotations

from app.models import Profile


def generate_markdown_cv(profile: Profile) -> str:
    """Verilen profilden zengin GitHub-Flavored Markdown CV metni oluşturur."""
    c = profile.contact
    lines = []

    # Header
    lines.append(f"# {c.full_name}")
    lines.append(f"### **{c.title}**")

    # Contacts
    contacts = []
    if c.email:
        contacts.append(f"📧 [{c.email}](mailto:{c.email})")
    if c.phone:
        contacts.append(f"📱 {c.phone}")
    if c.location:
        contacts.append(f"📍 {c.location}")
    if c.linkedin:
        contacts.append(f"💼 [LinkedIn]({c.linkedin})")
    if c.github:
        contacts.append(f"💻 [GitHub]({c.github})")
    if c.website:
        contacts.append(f"🌐 [Web]({c.website})")

    lines.append(" • ".join(contacts))
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    if profile.summary:
        lines.append("## 📝 Profesyonel Özet")
        lines.append(profile.summary.strip())
        lines.append("")

    # Experience
    if profile.experience:
        lines.append("## 💼 İş Deneyimi")
        for exp in profile.experience:
            end = exp.end_date or "Devam Ediyor"
            loc = f" *({exp.location})*" if exp.location else ""
            lines.append(f"### **{exp.role}** — {exp.company}{loc}")
            lines.append(f"*{exp.start_date} – {end}*")
            lines.append("")
            for hl in exp.highlights:
                lines.append(f"- {hl}")
            if exp.tech_stack:
                lines.append(f"  - **Teknolojiler:** `{', '.join(exp.tech_stack)}`")
            lines.append("")

    # Education
    if profile.education:
        lines.append("## 🎓 Eğitim")
        for edu in profile.education:
            end = edu.end_date or ""
            date_str = f"({edu.start_date} – {end})" if end else f"({edu.start_date})"
            fld = f" — {edu.field}" if edu.field else ""
            lines.append(f"- **{edu.school}** | {edu.degree}{fld} *{date_str}*")
        lines.append("")

    # Skills
    if profile.skills:
        lines.append("## 🛠️ Yetenekler")
        for sg in profile.skills:
            lines.append(f"- **{sg.category}:** {', '.join(sg.items)}")
        lines.append("")

    # Projects
    if profile.projects:
        lines.append("## 🚀 Projeler")
        for proj in profile.projects:
            url_str = f" [🔗 Link]({proj.url})" if proj.url else ""
            lines.append(f"### **{proj.name}**{url_str}")
            if proj.description:
                lines.append(f"{proj.description}")
            if proj.technologies:
                lines.append(f"- **Kullanılan Teknolojiler:** `{', '.join(proj.technologies)}`")
            lines.append("")

    # Certifications & Languages
    extras = []
    if profile.certifications:
        extras.append(f"**Sertifikalar:** {', '.join(profile.certifications)}")
    if profile.languages:
        extras.append(f"**Diller:** {', '.join(profile.languages)}")

    if extras:
        lines.append("## 🌐 Sertifikalar & Diller")
        for ex in extras:
            lines.append(f"- {ex}")
        lines.append("")

    return "\n".join(lines)
