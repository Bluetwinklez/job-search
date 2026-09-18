"""İş Arama Asistanı — web arayüzü.

Çalıştırma:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from app.cover_letter import generate_cover_letter, render_letter_pdf
from app.cv_generator import build_cv
from app.cv_rewrite import rewrite_cv
from app.cv_tailor import tailor_profile
from app.job_search import (
    ALL_SITES,
    STATUSES,
    get_job,
    get_matched_skills,
    get_stats,
    list_jobs,
    save_jobs,
    search_jobs,
    set_status,
)
from app.models import Profile

PROFILE_PATH = Path("data/profile.json")
EXAMPLE_PROFILE_PATH = Path("data/profile.example.json")
DB_PATH = Path("data/jobs.db")

st.set_page_config(page_title="İş Arama Asistanı", page_icon="📋", layout="wide")

with st.sidebar:
    st.header("⚙️ Yapay Zeka Ayarları")
    st.caption("Claude API özelliklerini (CV yeniden yazma & uyarlama) kullanmak için anahtarınızı girebilirsiniz:")
    api_key_input = st.text_input(
        "Anthropic API Anahtarı",
        type="password",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="sk-ant-... ile başlayan anahtarınız.",
    )
    model_choice = st.selectbox(
        "Claude Modeli",
        options=[
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        index=0,
    )
    if api_key_input:
        os.environ["ANTHROPIC_API_KEY"] = api_key_input



def load_profile_text() -> str:
    path = PROFILE_PATH if PROFILE_PATH.exists() else EXAMPLE_PROFILE_PATH
    return path.read_text(encoding="utf-8")


def try_load_profile() -> Profile | None:
    if not PROFILE_PATH.exists():
        return None
    try:
        return Profile.model_validate(json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError):
        return None


st.title("📋 İş Arama Asistanı")
st.caption("Merkezi profilinden ATS-dostu CV üret, çoklu platformdan iş ara, başvurularını takip et.")

tab_profile, tab_cv, tab_search, tab_tracker, tab_letter = st.tabs(
    ["Profil", "CV Oluştur", "İş Ara", "Başvurularım", "Ön Yazı"]
)

# ---------------------------------------------------------------- Profil ---
with tab_profile:
    st.subheader("Merkezi Profil")
    st.caption(
        "Tüm CV ve eşleşme skoru hesaplamaları bu JSON'dan beslenir. "
        "Alan tanımları için app/models.py içindeki şemaya bakabilirsin."
    )

    with st.expander("Var olan bir CV'yi yükle ve yeniden yaz (Claude ile)"):
        st.caption(
            "Elindeki CV'yi (.pdf veya .txt) yükle ya da metnini yapıştır. Claude yeni bir "
            "deneyim/başarı uydurmaz — yalnızca CV'de zaten var olan bilgileri ATS ve işe "
            "alım uzmanının olumlu değerlendireceği şekilde yeniden yazar ve yapılandırır. "
            "Çalışması için ortamda ANTHROPIC_API_KEY tanımlı olmalı."
        )
        uploaded_cv = st.file_uploader("CV dosyası (.pdf, .txt)", type=["pdf", "txt"])
        pasted_cv = st.text_area("veya CV metnini buraya yapıştır", height=150, key="raw_cv_paste")
        if st.button("CV'yi Yeniden Yaz", type="primary"):
            raw_text = ""
            if uploaded_cv is not None:
                if uploaded_cv.name.lower().endswith(".pdf"):
                    import pypdf

                    reader = pypdf.PdfReader(uploaded_cv)
                    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
                else:
                    raw_text = uploaded_cv.read().decode("utf-8", errors="ignore")
            elif pasted_cv.strip():
                raw_text = pasted_cv

            if not raw_text.strip():
                st.error("Bir dosya yükle veya CV metnini yapıştır.")
            else:
                try:
                    with st.spinner("Claude CV'yi yeniden yazıyor..."):
                        rewritten = rewrite_cv(raw_text, model=model_choice, api_key=api_key_input or None)
                    st.session_state["profile_json_editor"] = json.dumps(
                        rewritten.model_dump(), ensure_ascii=False, indent=2
                    )
                    st.success("CV yeniden yazıldı. Aşağıdaki editörde inceleyip 'Kaydet'e basabilirsin.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Yeniden yazma başarısız oldu: {e}")

    active_prof = try_load_profile()
    if active_prof:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Deneyim", f"{len(active_prof.experience)} adet")
        m2.metric("Eğitim", f"{len(active_prof.education)} okul")
        m3.metric("Yetenek Grubu", f"{len(active_prof.skills)} kategori")
        m4.metric("Sertifika & Proje", f"{len(active_prof.certifications) + len(active_prof.projects)} kayıt")

    st.session_state.setdefault("profile_json_editor", load_profile_text())
    profile_text = st.text_area("profile.json", key="profile_json_editor", height=420)

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Kaydet", type="primary"):
            try:
                data = json.loads(profile_text)
                Profile.model_validate(data)
            except json.JSONDecodeError as e:
                st.error(f"Geçersiz JSON: {e}")
            except ValidationError as e:
                st.error(f"Profil şeması hatalı:\n{e}")
            else:
                PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
                PROFILE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                st.success(f"Kaydedildi: {PROFILE_PATH}")

# --------------------------------------------------------------- CV Oluştur -
with tab_cv:
    st.subheader("ATS-Dostu PDF CV")
    profile = try_load_profile()
    if profile is None:
        st.warning("Önce 'Profil' sekmesinden geçerli bir profil kaydet.")
    else:
        st.write(f"**{profile.contact.full_name}** — {profile.contact.title}")
        if st.button("PDF Oluştur", type="primary"):
            pdf = build_cv(profile)
            pdf_bytes = bytes(pdf.output())
            st.session_state["cv_pdf_bytes"] = pdf_bytes
            st.success("CV oluşturuldu.")
        if "cv_pdf_bytes" in st.session_state:
            st.download_button(
                "CV'yi indir (PDF)",
                data=st.session_state["cv_pdf_bytes"],
                file_name=f"{profile.contact.full_name.replace(' ', '_')}_CV.pdf",
                mime="application/pdf",
            )

        with st.expander("İlana özel uyarla (Claude ile)"):
            st.caption(
                "Bir ilan açıklaması yapıştır; Claude yeni bir deneyim/yetenek uydurmaz, "
                "yalnızca profildeki özeti bu ilana göre yeniden yazar ve mevcut deneyim/"
                "yetenekleri alaka düzeyine göre yeniden sıralar. Çalışması için ortamda "
                "ANTHROPIC_API_KEY tanımlı olmalı."
            )
            tailor_job_description = st.text_area("İlan açıklaması", height=150, key="tailor_job_description")
            if st.button("İlana Özel CV Oluştur"):
                if not tailor_job_description.strip():
                    st.error("İlan açıklamasını yapıştır.")
                else:
                    try:
                        with st.spinner("Claude profili bu ilana göre uyarlıyor..."):
                            tailored_profile, result = tailor_profile(
                                profile, tailor_job_description, model=model_choice, api_key=api_key_input or None
                            )
                        pdf = build_cv(tailored_profile)
                        st.session_state["tailored_cv_pdf_bytes"] = bytes(pdf.output())
                        st.session_state["tailored_missing_keywords"] = result.missing_keywords
                        st.success("İlana özel CV oluşturuldu.")
                    except Exception as e:
                        st.error(f"Uyarlama başarısız oldu: {e}")
            if "tailored_cv_pdf_bytes" in st.session_state:
                st.download_button(
                    "İlana özel CV'yi indir (PDF)",
                    data=st.session_state["tailored_cv_pdf_bytes"],
                    file_name=f"{profile.contact.full_name.replace(' ', '_')}_CV_ilana_ozel.pdf",
                    mime="application/pdf",
                )
                missing = st.session_state.get("tailored_missing_keywords") or []
                if missing:
                    st.caption("İlanda geçip profilinde bulunmayan anahtar kelimeler: " + ", ".join(missing))

# ------------------------------------------------------------------ İş Ara --
with tab_search:
    st.subheader("Çoklu Platformdan İş İlanı Ara")
    with st.form("search_form"):
        c1, c2 = st.columns(2)
        search_term = c1.text_input("Pozisyon / anahtar kelime", value="Backend Developer")
        location = c2.text_input("Konum", value="Istanbul, Turkey")
        sites = st.multiselect("Platformlar", options=ALL_SITES, default=ALL_SITES)
        c3, c4, c5 = st.columns(3)
        results = c3.number_input("Platform başına sonuç", min_value=1, max_value=50, value=10)
        hours_old = c4.number_input("Son X saat (0 = sınırsız)", min_value=0, value=0)
        country_indeed = c5.text_input("Indeed ülke", value="turkey")
        linkedin_desc = st.checkbox(
            "LinkedIn açıklamalarını da çek (eşleşme skoru için gerekir, daha yavaştır)",
            value=False,
        )
        submitted = st.form_submit_button("Ara", type="primary")

    if submitted:
        profile = try_load_profile()
        with st.spinner("İlanlar taranıyor..."):
            df, errors = search_jobs(
                search_term,
                location or None,
                sites,
                int(results),
                int(hours_old) or None,
                country_indeed,
                linkedin_desc,
            )
        for site, error in errors:
            st.warning(f"{site} taranamadı: {error}")
        if df is None or df.empty:
            st.info("Sonuç bulunamadı.")
        else:
            new_count = save_jobs(df, DB_PATH, profile)
            st.success(f"{len(df)} ilan tarandı, {new_count} yeni ilan kaydedildi.")
            show_cols = [c for c in ["site", "title", "company", "location", "job_url"] if c in df.columns]
            st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

# ------------------------------------------------------------ Başvurularım --
with tab_tracker:
    st.subheader("Başvuru Takibi")
    if not DB_PATH.exists():
        st.info("Henüz taranmış ilan yok. Önce 'İş Ara' sekmesinden arama yap.")
    else:
        stats = get_stats(DB_PATH)
        cols = st.columns(len(STATUSES) + 1)
        cols[0].metric("Toplam", stats["total"])
        for i, s in enumerate(STATUSES, start=1):
            cols[i].metric(s.capitalize(), stats["by_status"].get(s, 0))

        view_mode = st.radio("Görünüm Seçeneği", ["📊 Kanban Panosu", "📋 Tablo Listesi"], horizontal=True)

        if view_mode == "📊 Kanban Panosu":
            kanban_cols = st.columns(len(STATUSES))
            all_tracker_jobs = list_jobs(DB_PATH, limit=300)
            jobs_by_status = {s: [r for r in all_tracker_jobs if r["status"] == s] for s in STATUSES}

            status_emojis = {
                "yeni": "🆕",
                "başvuruldu": "📨",
                "mülakat": "💼",
                "teklif": "🎉",
                "reddedildi": "❌",
            }

            for col_idx, status_name in enumerate(STATUSES):
                with kanban_cols[col_idx]:
                    st.markdown(f"#### {status_emojis.get(status_name, '')} {status_name.capitalize()} ({len(jobs_by_status[status_name])})")
                    for job_item in jobs_by_status[status_name]:
                        with st.container(border=True):
                            score_text = f" · 🎯 %{int(job_item['match_score'] * 100)}" if job_item["match_score"] is not None else ""
                            st.markdown(f"**{job_item['title']}**")
                            st.caption(f"{job_item['company']} ({job_item['site'] or ''}){score_text}")
                            if job_item["notes"]:
                                st.caption(f"📝 {job_item['notes']}")

                            if status_name == "yeni":
                                if st.button("Başvur ➡️", key=f"kb_app_{job_item['job_url']}"):
                                    set_status(DB_PATH, job_item["job_url"], "başvuruldu")
                                    st.rerun()
                            elif status_name == "başvuruldu":
                                c_k1, c_k2 = st.columns(2)
                                if c_k1.button("Mülakat 💼", key=f"kb_int_{job_item['job_url']}"):
                                    set_status(DB_PATH, job_item["job_url"], "mülakat")
                                    st.rerun()
                                if c_k2.button("Red ❌", key=f"kb_rej_{job_item['job_url']}"):
                                    set_status(DB_PATH, job_item["job_url"], "reddedildi")
                                    st.rerun()
                            elif status_name == "mülakat":
                                c_k1, c_k2 = st.columns(2)
                                if c_k1.button("Teklif 🎉", key=f"kb_off_{job_item['job_url']}"):
                                    set_status(DB_PATH, job_item["job_url"], "teklif")
                                    st.rerun()
                                if c_k2.button("Red ❌", key=f"kb_rej2_{job_item['job_url']}"):
                                    set_status(DB_PATH, job_item["job_url"], "reddedildi")
                                    st.rerun()

        st.divider()
        st.subheader("İlan Detayları ve Durum Yönetimi")
        status_filter = st.selectbox("Duruma göre filtrele", options=["(hepsi)"] + STATUSES)
        rows = list_jobs(
            DB_PATH,
            limit=200,
            status=None if status_filter == "(hepsi)" else status_filter,
        )
        if not rows:
            st.info("Kayıt bulunamadı.")
        else:
            df = pd.DataFrame([dict(r) for r in rows])
            st.dataframe(
                df[["title", "company", "site", "location", "match_score", "status", "job_url"]],
                use_container_width=True,
                hide_index=True,
            )

            col_csv, _ = st.columns([1, 3])
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            col_csv.download_button(
                "📥 Başvuruları CSV olarak indir",
                data=csv_data,
                file_name="basvurularim.csv",
                mime="text/csv",
            )


            st.markdown("**Durum güncelle & Detay Gör**")
            options = {f"{r['title']} — {r['company']} ({r['job_url']})": r["job_url"] for r in rows}
            selected_label = st.selectbox("İlan seç", options=list(options.keys()))

            selected_url = options[selected_label]
            selected_job_data = get_job(DB_PATH, selected_url)
            if selected_job_data:
                prof_for_match = try_load_profile()
                if prof_for_match:
                    full_text = f"{selected_job_data['title'] or ''} {selected_job_data['description'] or ''}"
                    matched_kws = get_matched_skills(full_text, prof_for_match)
                    if matched_kws:
                        st.info(f"🎯 Bu ilanla eşleşen yetenekleriniz: **{', '.join(matched_kws)}**")

            new_status = st.selectbox("Yeni durum", options=STATUSES)
            notes = st.text_input("Not (opsiyonel)")

            if new_status == "mülakat" or (selected_job_data and selected_job_data["status"] == "mülakat"):
                with st.expander("📅 Mülakatı Takvime Ekle (.ics İndir)", expanded=True):
                    col_m1, col_m2 = st.columns(2)
                    interview_date = col_m1.date_input("Mülakat Tarihi", key="interview_date")
                    interview_time = col_m2.time_input("Mülakat Saati", key="interview_time")
                    meeting_link = st.text_input(
                        "Toplantı Linki veya Konum",
                        placeholder="https://meet.google.com/... veya Ofis Adresi",
                        key="meeting_link",
                    )
                    duration = st.slider("Tahmini Süre (dakika)", min_value=15, max_value=120, value=45, step=15)

                    if selected_job_data:
                        from datetime import datetime
                        from app.calendar_export import generate_ics_event

                        dt_start = datetime.combine(interview_date, interview_time)
                        ics_content = generate_ics_event(
                            title=selected_job_data["title"] or "İş Mülakatı",
                            company=selected_job_data["company"] or "",
                            start_time=dt_start,
                            duration_minutes=duration,
                            location_or_url=meeting_link or None,
                            notes=notes or selected_job_data["notes"],
                        )
                        st.download_button(
                            "📅 Takvim Dosyasını İndir (.ics)",
                            data=ics_content,
                            file_name=f"mulakat_{(selected_job_data['company'] or 'etkinlik').replace(' ', '_')}.ics",
                            mime="text/calendar",
                        )

            if st.button("Güncelle"):
                job_url = options[selected_label]
                set_status(DB_PATH, job_url, new_status, notes or None)
                st.success("Güncellendi.")
                st.rerun()


# ------------------------------------------------------------------ Ön Yazı -
with tab_letter:
    st.subheader("Ön Yazı Taslağı")
    profile = try_load_profile()
    if profile is None:
        st.warning("Önce 'Profil' sekmesinden geçerli bir profil kaydet.")
    else:
        st.session_state.setdefault("letter_title", "Backend Developer")
        st.session_state.setdefault("letter_company", "")
        st.session_state.setdefault("letter_description", "")

        if DB_PATH.exists():
            tracked_rows = list_jobs(DB_PATH, limit=100)
            if tracked_rows:
                label_to_url = {f"{r['title']} — {r['company']}": r["job_url"] for r in tracked_rows}
                selected_label = st.selectbox(
                    "Kayıtlı bir ilandan doldur (opsiyonel)",
                    options=["(manuel gir)"] + list(label_to_url.keys()),
                )
                if selected_label != "(manuel gir)" and st.button("Bu ilandan doldur"):
                    job = get_job(DB_PATH, label_to_url[selected_label])
                    if job:
                        st.session_state["letter_title"] = job["title"] or ""
                        st.session_state["letter_company"] = job["company"] or ""
                        st.session_state["letter_description"] = job["description"] or ""
                        st.rerun()

        job_title = st.text_input("Pozisyon adı", key="letter_title")
        company = st.text_input("Şirket adı", key="letter_company")
        job_description = st.text_area(
            "İlan açıklaması (opsiyonel, eşleşen yetenekleri öne çıkarmak için)",
            key="letter_description",
            height=150,
        )
        if st.button("Taslak Oluştur", type="primary"):
            if not company:
                st.error("Şirket adını gir.")
            else:
                letter = generate_cover_letter(profile, job_title, company, job_description or None)
                st.session_state["cover_letter_text"] = letter
        if "cover_letter_text" in st.session_state:
            edited = st.text_area("Taslak (düzenlenebilir)", value=st.session_state["cover_letter_text"], height=300)
            dl_col1, dl_col2 = st.columns(2)
            dl_col1.download_button("Metni indir (.txt)", data=edited, file_name="on_yazi.txt", mime="text/plain")
            pdf_bytes = bytes(render_letter_pdf(edited).output())
            dl_col2.download_button(
                "PDF olarak indir", data=pdf_bytes, file_name="on_yazi.pdf", mime="application/pdf"
            )
