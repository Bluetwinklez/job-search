"""ATS-Dostu DOCX (Microsoft Word) CV üretici modülü."""

from __future__ import annotations

import io
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.models import Profile


def build_docx(profile: Profile) -> Document:
    """Profili standart ATS dostu, tek sütunlu Microsoft Word (.docx) belgesine dönüştürür."""
    doc = Document()

    # Sayfa kenar boşlukları (Standart 1 inç / 2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Başlık: Ad Soyad
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_name = p_name.add_run(profile.contact.full_name)
    run_name.font.name = "Arial"
    run_name.font.size = Pt(20)
    run_name.bold = True
    run_name.font.color.rgb = RGBColor(28, 56, 111)  # Klasik Lacivert
    p_name.paragraph_format.space_after = Pt(2)

    # Ünvan
    p_title = doc.add_paragraph()
    run_title = p_title.add_run(profile.contact.title)
    run_title.font.name = "Arial"
    run_title.font.size = Pt(12)
    run_title.font.color.rgb = RGBColor(80, 80, 80)
    p_title.paragraph_format.space_after = Pt(4)

    # İletişim Bilgileri
    contact_parts = [str(profile.contact.email)]
    if profile.contact.phone:
        contact_parts.append(profile.contact.phone)
    if profile.contact.location:
        contact_parts.append(profile.contact.location)
    if profile.contact.linkedin:
        contact_parts.append(profile.contact.linkedin)
    if profile.contact.github:
        contact_parts.append(profile.contact.github)

    p_contact = doc.add_paragraph()
    run_contact = p_contact.add_run("  •  ".join(contact_parts))
    run_contact.font.name = "Arial"
    run_contact.font.size = Pt(9.5)
    run_contact.font.color.rgb = RGBColor(100, 100, 100)
    p_contact.paragraph_format.space_after = Pt(12)

    def add_section_header(title: str):
        p_sec = doc.add_paragraph()
        run_sec = p_sec.add_run(title.upper())
        run_sec.font.name = "Arial"
        run_sec.font.size = Pt(11)
        run_sec.bold = True
        run_sec.font.color.rgb = RGBColor(28, 56, 111)
        p_sec.paragraph_format.space_before = Pt(10)
        p_sec.paragraph_format.space_after = Pt(3)

    # Özet
    if profile.summary:
        add_section_header("Özet")
        p_sum = doc.add_paragraph()
        run_sum = p_sum.add_run(profile.summary)
        run_sum.font.name = "Arial"
        run_sum.font.size = Pt(10)
        p_sum.paragraph_format.space_after = Pt(8)

    # Deneyim
    if profile.experience:
        add_section_header("İş Deneyimi")
        for exp in profile.experience:
            p_exp = doc.add_paragraph()
            r_role = p_exp.add_run(f"{exp.role} — {exp.company}")
            r_role.font.name = "Arial"
            r_role.font.size = Pt(10.5)
            r_role.bold = True

            end = exp.end_date or "Devam Ediyor"
            loc = f" | {exp.location}" if exp.location else ""
            r_date = p_exp.add_run(f"\n{exp.start_date} – {end}{loc}")
            r_date.font.name = "Arial"
            r_date.font.size = Pt(9)
            r_date.italic = True
            r_date.font.color.rgb = RGBColor(100, 100, 100)
            p_exp.paragraph_format.space_after = Pt(2)

            for hl in exp.highlights:
                p_bullet = doc.add_paragraph(style="List Bullet")
                r_hl = p_bullet.add_run(hl)
                r_hl.font.name = "Arial"
                r_hl.font.size = Pt(9.5)
                p_bullet.paragraph_format.space_after = Pt(1.5)

            if exp.tech_stack:
                p_tech = doc.add_paragraph()
                r_tech_lbl = p_tech.add_run("Kullanılan Teknolojiler: ")
                r_tech_lbl.font.name = "Arial"
                r_tech_lbl.font.size = Pt(9)
                r_tech_lbl.bold = True
                r_tech = p_tech.add_run(", ".join(exp.tech_stack))
                r_tech.font.name = "Arial"
                r_tech.font.size = Pt(9)
                p_tech.paragraph_format.space_after = Pt(6)

    # Eğitim
    if profile.education:
        add_section_header("Eğitim")
        for edu in profile.education:
            p_edu = doc.add_paragraph()
            r_sch = p_edu.add_run(edu.school)
            r_sch.font.name = "Arial"
            r_sch.font.size = Pt(10)
            r_sch.bold = True

            degree_str = f" — {edu.degree}"
            if edu.field:
                degree_str += f", {edu.field}"
            r_deg = p_edu.add_run(degree_str)
            r_deg.font.name = "Arial"
            r_deg.font.size = Pt(10)

            end_str = f" – {edu.end_date}" if edu.end_date else ""
            r_yr = p_edu.add_run(f" ({edu.start_date}{end_str})")
            r_yr.font.name = "Arial"
            r_yr.font.size = Pt(9)
            r_yr.font.color.rgb = RGBColor(100, 100, 100)
            p_edu.paragraph_format.space_after = Pt(3)

    # Yetenekler
    if profile.skills:
        add_section_header("Yetenekler")
        for sg in profile.skills:
            p_sk = doc.add_paragraph()
            r_cat = p_sk.add_run(f"{sg.category}: ")
            r_cat.font.name = "Arial"
            r_cat.font.size = Pt(9.5)
            r_cat.bold = True
            r_items = p_sk.add_run(", ".join(sg.items))
            r_items.font.name = "Arial"
            r_items.font.size = Pt(9.5)
            p_sk.paragraph_format.space_after = Pt(2)

    # Sertifikalar & Projeler
    if profile.certifications or profile.projects:
        add_section_header("Sertifikalar & Projeler")
        if profile.certifications:
            p_cert = doc.add_paragraph()
            r_clbl = p_cert.add_run("Sertifikalar: ")
            r_clbl.font.name = "Arial"
            r_clbl.font.size = Pt(9.5)
            r_clbl.bold = True
            r_citems = p_cert.add_run(", ".join(profile.certifications))
            r_citems.font.name = "Arial"
            r_citems.font.size = Pt(9.5)
            p_cert.paragraph_format.space_after = Pt(3)

        for proj in profile.projects:
            p_pr = doc.add_paragraph(style="List Bullet")
            r_pn = p_pr.add_run(f"{proj.name}: ")
            r_pn.font.name = "Arial"
            r_pn.font.size = Pt(9.5)
            r_pn.bold = True
            desc = proj.description or ""
            if proj.technologies:
                desc += f" (Teknolojiler: {', '.join(proj.technologies)})"
            r_pd = p_pr.add_run(desc)
            r_pd.font.name = "Arial"
            r_pd.font.size = Pt(9.5)
            p_pr.paragraph_format.space_after = Pt(1.5)

    return doc


def get_docx_bytes(profile: Profile) -> bytes:
    """DOCX belgesini byte dizisi olarak döner."""
    doc = build_docx(profile)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
