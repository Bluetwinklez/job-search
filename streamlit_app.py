"""İş Arama Asistanı — web arayüzü.

Çalıştırma:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from pydantic import ValidationError

from app.cover_letter import generate_cover_letter, render_letter_pdf
from app.cv_generator import build_cv
from app.cv_rewrite import rewrite_cv
from app.cv_tailor import tailor_profile
from app.job_search import ALL_SITES, STATUSES, get_job, get_stats, list_jobs, save_jobs, search_jobs, set_status
from app.models import Profile

PROFILE_PATH = Path("data/profile.json")
EXAMPLE_PROFILE_PATH = Path("data/profile.example.json")
DB_PATH = Path("data/jobs.db")

st.set_page_config(page_title="İş Arama Asistanı", page_icon="📋", layout="wide")


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
                        rewritten = rewrite_cv(raw_text)
                    st.session_state["profile_json_editor"] = json.dumps(
                        rewritten.model_dump(), ensure_ascii=False, indent=2
                    )
                    st.success("CV yeniden yazıldı. Aşağıdaki editörde inceleyip 'Kaydet'e basabilirsin.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Yeniden yazma başarısız oldu: {e}")

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
                            tailored_profile, result = tailor_profile(profile, tailor_job_description)
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

            st.markdown("**Durum güncelle**")
            options = {f"{r['title']} — {r['company']} ({r['job_url']})": r["job_url"] for r in rows}
            selected_label = st.selectbox("İlan seç", options=list(options.keys()))
            new_status = st.selectbox("Yeni durum", options=STATUSES)
            notes = st.text_input("Not (opsiyonel)")
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
