"""Görsel tasarım bileşenleri, marka kimliği, profil doluluk hesabı ve boş durum (empty state) yöneticisi."""

from __future__ import annotations

from typing import List, Tuple, Optional
from app.models import Profile


def calculate_profile_completeness(profile: Optional[Profile]) -> Tuple[int, List[str]]:
    """Profilin tamamlanma yüzdesini (0-100) ve eksik kalan adımların listesini döner."""
    if not profile:
        return 0, ["Profil bilgilerinizi doldurun."]

    score = 0
    missing = []

    # İletişim Bilgileri (20 Puan)
    contact = profile.contact
    if contact.full_name and contact.email:
        score += 15
        if contact.phone or contact.linkedin or contact.location:
            score += 5
        else:
            missing.append("İletişim: Telefon veya LinkedIn bağlantısı ekleyin (+5 puan)")
    else:
        missing.append("İletişim: Ad soyad ve e-posta girin (+15 puan)")

    # Özet (15 Puan)
    if profile.summary and len(profile.summary.strip()) >= 30:
        score += 15
    else:
        missing.append("Özet: Kendinizi anlatan profesyonel bir özet yazın (+15 puan)")

    # Deneyim (25 Puan)
    if profile.experience:
        score += 15
        has_highlights = any(len(exp.highlights) > 0 for exp in profile.experience)
        if has_highlights:
            score += 10
        else:
            missing.append("Deneyim: En az bir iş için başarı/görev maddesi ekleyin (+10 puan)")
    else:
        missing.append("Deneyim: En az bir iş deneyimi ekleyin (+25 puan)")

    # Eğitim (15 Puan)
    if profile.education:
        score += 15
    else:
        missing.append("Eğitim: Mezun olduğunuz okul/üniversiteyi ekleyin (+15 puan)")

    # Yetenekler (15 Puan)
    if profile.skills and any(len(sg.items) > 0 for sg in profile.skills):
        score += 15
    else:
        missing.append("Yetenekler: Teknik veya uzmanlık yetenekleri ekleyin (+15 puan)")

    # Ekstralar: Diller, Sertifikalar veya Projeler (10 Puan)
    extras = len(profile.languages) + len(profile.certifications) + len(profile.projects)
    if extras > 0:
        score += 10
    else:
        missing.append("Ekstralar: Yabancı dil, sertifika veya proje ekleyin (+10 puan)")

    return min(score, 100), missing


def render_breadcrumb_html(active_profile: str, completeness_score: int, job_count: int) -> str:
    """Üst kısımda her sekmede sabit görünen durum ve breadcrumb çubuğu."""
    badge_color = "#10b981" if completeness_score >= 80 else ("#f59e0b" if completeness_score >= 50 else "#ef4444")
    return f"""
    <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, rgba(79, 70, 229, 0.08) 0%, rgba(99, 102, 241, 0.02) 100%);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 10px;
        padding: 8px 16px;
        margin-bottom: 18px;
        font-size: 0.88rem;
    ">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 600; color: #4f46e5;">👤 Aktif Profil:</span>
            <span style="background: rgba(99, 102, 241, 0.15); color: #4338ca; padding: 2px 10px; border-radius: 20px; font-weight: 700;">{active_profile}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 20px;">
            <div>
                <span style="color: #6b7280;">Profil Doluluğu:</span>
                <span style="font-weight: 700; color: {badge_color}; margin-left: 4px;">%{completeness_score}</span>
            </div>
            <div>
                <span style="color: #6b7280;">Kayıtlı İlan:</span>
                <span style="font-weight: 700; color: #1f2937; margin-left: 4px;">{job_count}</span>
            </div>
        </div>
    </div>
    """


def render_empty_state_html(title: str, description: str, icon: str = "🔍") -> str:
    """Veri bulunmadığında gösterilecek rehber boş durum kartı."""
    return f"""
    <div style="
        text-align: center;
        padding: 40px 20px;
        background: rgba(128, 128, 128, 0.03);
        border: 2px dashed rgba(128, 128, 128, 0.2);
        border-radius: 14px;
        margin: 20px 0;
    ">
        <div style="font-size: 2.5rem; margin-bottom: 8px;">{icon}</div>
        <h3 style="margin: 0 0 6px 0; font-weight: 700; color: #374151;">{title}</h3>
        <p style="margin: 0; color: #6b7280; max-width: 480px; margin: 0 auto; font-size: 0.95rem;">{description}</p>
    </div>
    """


def render_cv_html_preview(profile: Profile, theme_name: str = "classic_navy") -> str:
    """PDF indirmeden tarayıcıda canlı ve şık bir CV önizlemesi sunar."""
    from app.cv_generator import THEMES

    theme = THEMES.get(theme_name, THEMES["classic_navy"])
    accent_rgb = theme.get("accent", (28, 56, 111))
    accent_hex = f"rgb({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]})"

    contact = profile.contact
    contact_parts = [contact.email]
    if contact.phone:
        contact_parts.append(contact.phone)
    if contact.location:
        contact_parts.append(contact.location)
    if contact.linkedin:
        contact_parts.append(contact.linkedin)

    exp_html = ""
    for exp in profile.experience:
        end = exp.end_date or "Devam Ediyor"
        hl_items = "".join(f"<li style='margin-bottom: 3px;'>{hl}</li>" for hl in exp.highlights)
        tech = f"<div style='font-size: 0.8rem; color: #6b7280; margin-top: 4px;'><strong>Teknolojiler:</strong> {', '.join(exp.tech_stack)}</div>" if exp.tech_stack else ""
        exp_html += f"""
        <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-weight: 700; color: #1f2937;">
                <span>{exp.role} — {exp.company}</span>
                <span style="font-size: 0.85rem; color: #6b7280; font-weight: normal;">{exp.start_date} – {end}</span>
            </div>
            <ul style="margin: 4px 0 0 0; padding-left: 20px; font-size: 0.9rem; color: #4b5563;">
                {hl_items}
            </ul>
            {tech}
        </div>
        """

    edu_html = ""
    for edu in profile.education:
        end = edu.end_date or ""
        date_str = f"({edu.start_date} – {end})" if end else f"({edu.start_date})"
        edu_html += f"""
        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 6px;">
            <span><strong>{edu.school}</strong> — {edu.degree} {f'({edu.field})' if edu.field else ''}</span>
            <span style="color: #6b7280;">{date_str}</span>
        </div>
        """

    skills_html = ""
    for sg in profile.skills:
        skills_html += f"<div style='font-size: 0.9rem; margin-bottom: 4px;'><strong>{sg.category}:</strong> {', '.join(sg.items)}</div>"

    return f"""
    <div style="
        background: #ffffff;
        color: #1f2937;
        padding: 32px 40px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #e5e7eb;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 800px;
        margin: 0 auto;
    ">
        <div style="border-bottom: 2px solid {accent_hex}; padding-bottom: 12px; margin-bottom: 16px;">
            <h1 style="margin: 0; color: {accent_hex}; font-size: 1.8rem; font-weight: 800;">{contact.full_name}</h1>
            <div style="font-size: 1.05rem; color: #4b5563; margin-top: 4px; font-weight: 600;">{contact.title}</div>
            <div style="font-size: 0.85rem; color: #6b7280; margin-top: 6px;">{'  •  '.join(contact_parts)}</div>
        </div>

        {f'<div style="margin-bottom: 16px;"><h4 style="margin: 0 0 6px 0; color: {accent_hex}; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;">Özet</h4><p style="margin: 0; font-size: 0.92rem; line-height: 1.5; color: #374151;">{profile.summary}</p></div>' if profile.summary else ''}

        {f'<div style="margin-bottom: 16px;"><h4 style="margin: 0 0 8px 0; color: {accent_hex}; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;">İş Deneyimi</h4>{exp_html}</div>' if profile.experience else ''}

        {f'<div style="margin-bottom: 16px;"><h4 style="margin: 0 0 8px 0; color: {accent_hex}; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;">Eğitim</h4>{edu_html}</div>' if profile.education else ''}

        {f'<div style="margin-bottom: 16px;"><h4 style="margin: 0 0 8px 0; color: {accent_hex}; text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;">Yetenekler</h4>{skills_html}</div>' if profile.skills else ''}
    </div>
    """


def render_donut_chart_html(data: dict[str, int], title: str = "Başvuru Durumu Dağılımı") -> str:
    """Başvuru durumları veya platformlar için temiz, modern SVG halka/pasta (donut) grafiği üretir."""
    total = sum(data.values())
    if total == 0:
        return render_empty_state_html(title, "Gösterilecek veri bulunamadı.", "📊")

    palette = {
        "yeni": "#3b82f6",
        "başvuruldu": "#8b5cf6",
        "mülakat": "#f59e0b",
        "teklif": "#10b981",
        "reddedildi": "#ef4444",
    }
    fallback_colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#6366f1", "#14b8a6"]

    r = 50
    circ = 2 * 3.14159265 * r
    accumulated_pct = 0.0

    slices_svg = []
    legend_items = []

    for idx, (label, count) in enumerate(data.items()):
        if count <= 0:
            continue
        pct = count / total
        color = palette.get(label.lower(), fallback_colors[idx % len(fallback_colors)])
        dash_len = pct * circ
        offset = -(accumulated_pct * circ)
        accumulated_pct += pct

        slices_svg.append(
            f'<circle cx="70" cy="70" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="22" stroke-dasharray="{dash_len:.2f} {circ:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 70 70)" />'
        )

        pct_label = f"%{int(round(pct * 100))}"
        legend_items.append(
            f"""<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; font-size: 0.88rem;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: {color};"></span>
                    <span style="color: #374151; font-weight: 500;">{label.capitalize()}</span>
                </div>
                <div style="display: flex; gap: 10px;">
                    <span style="font-weight: 700; color: #1f2937;">{count}</span>
                    <span style="color: #9ca3af; font-size: 0.8rem; width: 36px; text-align: right;">{pct_label}</span>
                </div>
            </div>"""
        )

    slices_str = "\n".join(slices_svg)
    legend_str = "\n".join(legend_items)

    return f"""
    <div style="
        background: #ffffff;
        border: 1px solid rgba(229, 231, 235, 0.8);
        border-radius: 14px;
        padding: 20px 24px;
        margin: 12px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    ">
        <h4 style="margin: 0 0 16px 0; font-size: 1rem; font-weight: 700; color: #1f2937;">📊 {title}</h4>
        <div style="display: flex; align-items: center; justify-content: space-around; flex-wrap: wrap; gap: 20px;">
            <div style="position: relative; width: 140px; height: 140px;">
                <svg width="140" height="140" viewBox="0 0 140 140">
                    <circle cx="70" cy="70" r="{r}" fill="none" stroke="#f3f4f6" stroke-width="22" />
                    {slices_str}
                </svg>
                <div style="
                    position: absolute;
                    top: 0; left: 0; width: 140px; height: 140px;
                    display: flex; flex-direction: column; align-items: center; justify-content: center;
                    pointer-events: none;
                ">
                    <span style="font-size: 1.25rem; font-weight: 800; color: #111827;">{total}</span>
                    <span style="font-size: 0.72rem; color: #6b7280; text-transform: uppercase; font-weight: 600;">Toplam</span>
                </div>
            </div>
            <div style="min-width: 220px; flex: 1;">
                {legend_str}
            </div>
        </div>
    </div>
    """
