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

from app import profile_store
from app.cover_letter import (
    generate_bulk_cover_letters,
    generate_cover_letter,
    generate_cover_letter_english,
    render_letter_pdf,
)
from app.cv_generator import THEMES, build_cv
from app.cv_rewrite import rewrite_cv
from app.cv_tailor import tailor_profile
from app.job_comparator import compare_jobs
from app.job_search import (
    ALL_SITES,
    STATUSES,
    add_to_blacklist,
    add_watched_company,
    delete_interview_question,
    delete_saved_search,
    get_blacklist,
    get_job,
    get_matched_skills,
    get_stats,
    list_interview_questions,
    list_jobs,
    list_saved_searches,
    list_search_history,
    list_upcoming_interviews,
    list_watched_companies,
    log_search,
    remove_from_blacklist,
    remove_watched_company,
    save_interview_questions,
    save_jobs,
    save_search,
    search_jobs,
    set_interview_datetime,
    set_status,
    toggle_favorite,
    update_interview_answer,
)
from app.models import Profile

EXAMPLE_PROFILE_PATH = Path("data/profile.example.json")
DB_PATH = Path("data/jobs.db")

st.set_page_config(page_title="İş Arama Asistanı", page_icon="📋", layout="wide")

from app.ui_theme import apply_theme
apply_theme()

profile_store.ensure_migrated()

with st.sidebar:
    st.header("👤 Aktif Profil")
    st.caption("Farklı sektörler/pozisyonlar için ayrı profiller tutabilirsin.")
    _profiles = profile_store.list_profiles() or [profile_store.DEFAULT_PROFILE_NAME]

    if "_pending_active_profile" in st.session_state:
        st.session_state["active_profile"] = st.session_state.pop("_pending_active_profile")
    st.session_state.setdefault("active_profile", _profiles[0])
    if st.session_state["active_profile"] not in _profiles:
        st.session_state["active_profile"] = _profiles[0]
    st.selectbox("Profil", options=_profiles, key="active_profile")

    with st.expander("Yeni profil oluştur"):
        new_profile_name = st.text_input("Profil adı (ör. yazilim, saglik)", key="new_profile_name_input")
        if st.button("Oluştur", key="create_profile_btn"):
            if not new_profile_name.strip():
                st.error("Profil adı gir.")
            elif new_profile_name.strip() in _profiles:
                st.error("Bu isimde bir profil zaten var.")
            else:
                example_data = json.loads(EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8"))
                profile_store.save_profile(new_profile_name.strip(), example_data)
                st.session_state["_pending_active_profile"] = new_profile_name.strip()
                st.session_state.pop("profile_json_editor", None)
                st.rerun()

    st.divider()
    st.header("⚙️ Yapay Zeka Ayarları")
    st.caption("CV uyarlama, yeniden yazma ve analiz için yapay zeka sağlayıcınızı seçin:")

    from app.llm_client import PROVIDERS

    provider_choice = st.selectbox(
        "Yapay Zeka Sağlayıcısı",
        options=list(PROVIDERS.keys()),
        format_func=lambda k: PROVIDERS[k]["name"],
        key="ai_provider_select",
    )

    prov_info = PROVIDERS[provider_choice]
    env_var_name = prov_info["env_var"]
    api_key_input = st.text_input(
        f"{prov_info['name']} API Anahtarı",
        type="password",
        value=os.environ.get(env_var_name, ""),
        help=f"{env_var_name} ortam değişkeninden veya buradan girilebilir.",
        key=f"api_key_input_{provider_choice}",
    )
    model_choice = st.selectbox(
        "Model",
        options=prov_info["models"],
        index=0,
        key=f"model_choice_{provider_choice}",
    )
    if api_key_input:
        os.environ[env_var_name] = api_key_input

    st.divider()
    st.header("💾 Veri Yedekleme")
    with st.expander("📦 Yedek İndir / Yükle"):
        from app.backup import create_backup_zip, restore_backup_zip

        st.caption("Veritabanı, profil ve sürüm geçmişinizi tek tıkla ZIP olarak yedekleyin.")
        backup_bytes = create_backup_zip(Path("data"))
        st.download_button(
            "📥 Tam Yedek İndir (.zip)",
            data=backup_bytes,
            file_name="is_arama_asistani_yedek.zip",
            mime="application/zip",
            key="dl_backup_zip_btn",
        )

        st.markdown("---")
        st.caption("Var olan bir ZIP yedeğini sisteme yükle:")
        uploaded_backup = st.file_uploader("Yedek (.zip)", type=["zip"], key="backup_upload_zip")
        if st.button("Yedeği Geri Yükle", key="restore_backup_btn"):
            if uploaded_backup is not None:
                res = restore_backup_zip(uploaded_backup.read(), Path("data"))
                if res["success"]:
                    st.success(f"Yedek geri yüklendi! ({len(res['files_restored'])} dosya)")
                    st.rerun()
                else:
                    st.error(f"Geri yükleme hatası: {res['error']}")
            else:
                st.warning("Lütfen bir .zip dosyası seçin.")

PROFILE_PATH = profile_store.profile_path(st.session_state["active_profile"])


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

    editor_mode = st.radio(
        "Düzenleme Yöntemi",
        options=["📝 Form Editörü (Kolay)", "💻 JSON Editörü (Gelişmiş)"],
        horizontal=True,
        key="profile_editor_mode_choice",
    )

    if editor_mode == "📝 Form Editörü (Kolay)":
        if not active_prof:
            st.warning("Henüz geçerli bir profil yüklenmedi. Örnek profilden başlatılıyor.")
            active_prof = Profile.model_validate(json.loads(EXAMPLE_PROFILE_PATH.read_text(encoding="utf-8")))

        from app.profile_editor import profile_to_form_dict, form_dict_to_profile

        # Form state container
        form_state_key = f"_form_data_{st.session_state['active_profile']}"
        if form_state_key not in st.session_state or st.session_state.get("_last_form_loaded_for") != st.session_state["active_profile"]:
            st.session_state[form_state_key] = profile_to_form_dict(active_prof)
            st.session_state["_last_form_loaded_for"] = st.session_state["active_profile"]

        fd = st.session_state[form_state_key]

        with st.form("profile_interactive_form"):
            st.markdown("#### 👤 İletişim & Temel Bilgiler")
            c1, c2 = st.columns(2)
            with c1:
                fd["contact"]["full_name"] = st.text_input("Ad Soyad", value=fd["contact"]["full_name"])
                fd["contact"]["title"] = st.text_input("Ünvan / Pozisyon", value=fd["contact"]["title"])
                fd["contact"]["email"] = st.text_input("E-posta", value=fd["contact"]["email"])
                fd["contact"]["phone"] = st.text_input("Telefon", value=fd["contact"]["phone"])
            with c2:
                fd["contact"]["location"] = st.text_input("Konum / Şehir", value=fd["contact"]["location"])
                fd["contact"]["linkedin"] = st.text_input("LinkedIn", value=fd["contact"]["linkedin"])
                fd["contact"]["github"] = st.text_input("GitHub", value=fd["contact"]["github"])
                fd["contact"]["website"] = st.text_input("Kişisel Web Sitesi", value=fd["contact"]["website"])

            st.markdown("#### 📝 Profesyonel Özet")
            fd["summary"] = st.text_area("Özet Metni", value=fd.get("summary") or "", height=100)

            st.markdown("#### 💼 İş Deneyimleri")
            exp_to_remove = []
            for idx, exp in enumerate(fd["experience"]):
                with st.expander(f"📌 {exp.get('role') or 'Pozisyon'} @ {exp.get('company') or 'Şirket'}", expanded=(idx == 0)):
                    ec1, ec2, ec3 = st.columns([2, 2, 1])
                    exp["role"] = ec1.text_input(f"Pozisyon #{idx+1}", value=exp["role"], key=f"fe_role_{idx}")
                    exp["company"] = ec2.text_input(f"Şirket #{idx+1}", value=exp["company"], key=f"fe_comp_{idx}")
                    exp["location"] = ec3.text_input(f"Konum #{idx+1}", value=exp["location"], key=f"fe_loc_{idx}")

                    ec4, ec5 = st.columns(2)
                    exp["start_date"] = ec4.text_input(f"Başlangıç (ör. 2022-03) #{idx+1}", value=exp["start_date"], key=f"fe_sd_{idx}")
                    exp["end_date"] = ec5.text_input(f"Bitiş (boş ise Halen) #{idx+1}", value=exp["end_date"], key=f"fe_ed_{idx}")

                    exp["highlights"] = st.text_area(
                        f"Başarılar / Görevler (Her satır bir madde) #{idx+1}",
                        value=exp["highlights"],
                        height=100,
                        key=f"fe_hl_{idx}",
                    )
                    exp["tech_stack"] = st.text_input(
                        f"Kullanılan Teknolojiler (virgülle ayırın) #{idx+1}",
                        value=exp["tech_stack"],
                        key=f"fe_ts_{idx}",
                    )

            st.markdown("#### 🎓 Eğitim")
            for idx, edu in enumerate(fd["education"]):
                with st.expander(f"🎓 {edu.get('school') or 'Okul'} — {edu.get('degree') or 'Derece'}", expanded=(idx == 0)):
                    ed1, ed2, ed3 = st.columns([2, 1, 2])
                    edu["school"] = ed1.text_input(f"Okul / Üniversite #{idx+1}", value=edu["school"], key=f"fe_sch_{idx}")
                    edu["degree"] = ed2.text_input(f"Derece (Lisans, YL) #{idx+1}", value=edu["degree"], key=f"fe_deg_{idx}")
                    edu["field"] = ed3.text_input(f"Bölüm #{idx+1}", value=edu["field"], key=f"fe_fld_{idx}")

                    ed4, ed5 = st.columns(2)
                    edu["start_date"] = ed4.text_input(f"Başlangıç Yılı #{idx+1}", value=edu["start_date"], key=f"fe_esd_{idx}")
                    edu["end_date"] = ed5.text_input(f"Mezuniyet Yılı #{idx+1}", value=edu["end_date"], key=f"fe_eed_{idx}")

            st.markdown("#### 🛠️ Yetenek Grupları")
            for idx, sg in enumerate(fd["skills"]):
                sk1, sk2 = st.columns([1, 3])
                sg["category"] = sk1.text_input(f"Kategori #{idx+1}", value=sg["category"], key=f"fe_cat_{idx}")
                sg["items"] = sk2.text_input(f"Yetenekler (virgülle ayrılmış) #{idx+1}", value=sg["items"], key=f"fe_sk_{idx}")

            st.markdown("#### 🌐 Diller, Sertifikalar & Projeler")
            fd["languages"] = st.text_input("Diller (virgülle ayırın)", value=fd["languages"], help="ör. Türkçe (Anadil), İngilizce (C1)")
            fd["certifications"] = st.text_input("Sertifikalar (virgülle ayırın)", value=fd["certifications"], help="ör. AWS Solutions Architect, CKA")

            for idx, proj in enumerate(fd["projects"]):
                with st.expander(f"🚀 {proj.get('name') or 'Proje'} #{idx+1}", expanded=False):
                    p1, p2 = st.columns(2)
                    proj["name"] = p1.text_input(f"Proje Adı #{idx+1}", value=proj["name"], key=f"fe_pr_n_{idx}")
                    proj["url"] = p2.text_input(f"Proje Linki #{idx+1}", value=proj["url"], key=f"fe_pr_u_{idx}")
                    proj["description"] = st.text_input(f"Açıklama #{idx+1}", value=proj["description"], key=f"fe_pr_d_{idx}")
                    proj["technologies"] = st.text_input(f"Teknolojiler #{idx+1}", value=proj["technologies"], key=f"fe_pr_t_{idx}")

            save_form_btn = st.form_submit_button("💾 Form Değişikliklerini Kaydet", type="primary")
            if save_form_btn:
                try:
                    updated_profile = form_dict_to_profile(fd)
                    profile_store.save_profile(st.session_state["active_profile"], updated_profile.model_dump())
                    st.session_state["profile_json_editor"] = json.dumps(
                        updated_profile.model_dump(), ensure_ascii=False, indent=2
                    )
                    st.success("Profil formu başarıyla kaydedildi!")
                    st.rerun()
                except ValidationError as err:
                    st.error(f"Profil doğrulama hatası:\n{err}")
                except Exception as err:
                    st.error(f"Kaydetme başarısız: {err}")

    else:
        if st.session_state.get("_editor_loaded_for") != st.session_state["active_profile"]:
            st.session_state["profile_json_editor"] = load_profile_text()
            st.session_state["_editor_loaded_for"] = st.session_state["active_profile"]
        profile_text = st.text_area("profile.json", key="profile_json_editor", height=420)

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("Kaydet (JSON)", type="primary"):
                try:
                    data = json.loads(profile_text)
                    Profile.model_validate(data)
                except json.JSONDecodeError as e:
                    st.error(f"Geçersiz JSON: {e}")
                except ValidationError as e:
                    st.error(f"Profil şeması hatalı:\n{e}")
                else:
                    profile_store.save_profile(st.session_state["active_profile"], data)
                    st.session_state.pop(f"_form_data_{st.session_state['active_profile']}", None)
                    st.success(f"Kaydedildi: {PROFILE_PATH}")

    with st.expander("Sürüm geçmişi"):
        history = profile_store.list_history(st.session_state["active_profile"])
        if not history:
            st.caption("Henüz geçmiş sürüm yok — her kayıtta bir önceki hal burada saklanır.")
        else:
            selected_stamp = st.selectbox(
                "Geri dönülecek sürüm (tarih/saat, UTC)",
                options=history,
                format_func=lambda s: f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[9:11]}:{s[11:13]}:{s[13:15]}",
            )
            hist_col1, hist_col2 = st.columns([1, 3])
            if hist_col1.button("Bu sürüme dön"):
                old_text = profile_store.load_history_text(st.session_state["active_profile"], selected_stamp)
                if old_text:
                    st.session_state["profile_json_editor"] = old_text
                    st.session_state["_editor_loaded_for"] = st.session_state["active_profile"]
                    st.info("Eski sürüm editöre yüklendi. Kaydetmek için 'Kaydet'e bas.")
                    st.rerun()

# --------------------------------------------------------------- CV Oluştur -
with tab_cv:
    st.subheader("ATS-Dostu PDF CV")
    profile = try_load_profile()
    if profile is None:
        st.warning("Önce 'Profil' sekmesinden geçerli bir profil kaydet.")
    else:
        col_cv1, col_cv2 = st.columns([2, 1])
        with col_cv1:
            st.write(f"**{profile.contact.full_name}** — {profile.contact.title}")
        with col_cv2:
            selected_theme = st.selectbox(
                "CV Tasarım Teması",
                options=list(THEMES.keys()),
                format_func=lambda k: THEMES[k]["name"],
                key="cv_theme_select",
            )

        with st.expander("📷 Vesikalık fotoğraf ekle (opsiyonel)"):
            st.caption(
                "Bazı sektörlerde/ülkelerde fotoğraflı CV beklenir; ancak bazı ATS "
                "sistemleri görselli CV'leri daha zor ayrıştırabilir. Eklemek "
                "tamamen isteğe bağlıdır."
            )
            cv_photo = st.file_uploader("Fotoğraf (.jpg, .png)", type=["jpg", "jpeg", "png"], key="cv_photo_upload")

        if st.button("PDF Oluştur", type="primary"):
            photo_path = None
            if cv_photo is not None:
                import tempfile

                suffix = Path(cv_photo.name).suffix or ".jpg"
                tmp_photo = Path(tempfile.gettempdir()) / f"cv_photo_{st.session_state['active_profile']}{suffix}"
                tmp_photo.write_bytes(cv_photo.getvalue())
                photo_path = tmp_photo
            pdf = build_cv(profile, theme=selected_theme, photo_path=photo_path)
            pdf_bytes = bytes(pdf.output())
            st.session_state["cv_pdf_bytes"] = pdf_bytes
            st.success(f"CV oluşturuldu ({THEMES[selected_theme]['name']}).")
        col_dl1, col_dl2 = st.columns(2)
        if "cv_pdf_bytes" in st.session_state:
            col_dl1.download_button(
                "📄 CV'yi İndir (PDF)",
                data=st.session_state["cv_pdf_bytes"],
                file_name=f"{profile.contact.full_name.replace(' ', '_')}_CV.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        from app.docx_generator import get_docx_bytes

        docx_bytes = get_docx_bytes(profile)
        col_dl2.download_button(
            "📝 CV'yi İndir (Word / DOCX)",
            data=docx_bytes,
            file_name=f"{profile.contact.full_name.replace(' ', '_')}_CV.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

        with st.expander("🎯 ATS Uyumluluk Skoru & Denetim Raporu", expanded=True):
            from app.ats_scorer import score_profile

            report = score_profile(profile)

            c_sc1, c_sc2 = st.columns([1, 2])
            with c_sc1:
                st.metric("ATS Skoru", f"{report.total_score} / 100")
                st.progress(report.total_score / 100.0)
            with c_sc2:
                b = report.breakdown
                st.markdown(
                    f"- İletişim: **{b.contact_score}/15**\n"
                    f"- Özet: **{b.summary_score}/15**\n"
                    f"- Deneyim: **{b.experience_score}/30** (Sayısal Metrik: **{report.metric_mentions_count}**)\n"
                    f"- Yetenekler: **{b.skills_score}/25**\n"
                    f"- Eğitim: **{b.education_score}/15**"
                )

            if report.strengths:
                st.markdown("**Güçlü Yönler:**")
                for s in report.strengths:
                    st.caption(f"✅ {s}")

            if report.recommendations:
                st.markdown("**ATS Tavsiyeleri:**")
                for r in report.recommendations:
                    st.caption(f"💡 {r}")


        with st.expander("🌐 İngilizce CV Oluştur"):
            st.caption(
                "Profildeki gerçek bilgileri koruyarak (yeni bilgi uydurmadan) CV'yi "
                "İngilizceye çevirip İngilizce başlıklarla PDF üretir. Çalışması için "
                "ortamda ANTHROPIC_API_KEY tanımlı olmalı."
            )
            en_theme = st.selectbox(
                "Tema",
                options=list(THEMES.keys()),
                format_func=lambda k: THEMES[k]["name"],
                key="cv_en_theme_select",
            )
            if st.button("İngilizce CV Oluştur", key="generate_en_cv_btn"):
                try:
                    from app.cv_translate import translate_profile_to_english

                    with st.spinner("Profil İngilizceye çevriliyor..."):
                        translated_profile = translate_profile_to_english(
                            profile, model=model_choice, api_key=api_key_input or None
                        )
                    en_pdf = build_cv(translated_profile, theme=en_theme, language="en")
                    st.session_state["cv_en_pdf_bytes"] = bytes(en_pdf.output())
                    st.success("İngilizce CV oluşturuldu.")
                except Exception as exc:
                    st.error(f"İngilizce CV oluşturulamadı: {exc}")
            if "cv_en_pdf_bytes" in st.session_state:
                st.download_button(
                    "Download English CV (PDF)",
                    data=st.session_state["cv_en_pdf_bytes"],
                    file_name=f"{profile.contact.full_name.replace(' ', '_')}_CV_EN.pdf",
                    mime="application/pdf",
                    key="dl_en_cv_btn",
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

    st.session_state.setdefault("search_term_val", "Backend Developer")
    st.session_state.setdefault("location_val", "Istanbul, Turkey")
    st.session_state.setdefault("sites_val", ALL_SITES)
    st.session_state.setdefault("remote_val", False)

    with st.expander("📌 Kayıtlı Aramalar"):
        saved = list_saved_searches(DB_PATH) if DB_PATH.parent.exists() else []
        if not saved:
            st.caption("Henüz kayıtlı arama şablonu yok. Arama yaptıktan sonra aşağıdan kaydedebilirsin.")
        else:
            for s in saved:
                sc1, sc2, sc3 = st.columns([3, 1, 1])
                sc1.write(f"**{s['name']}** — {s['search_term']} @ {s['location'] or '(her yer)'}")
                if sc2.button("Çalıştır", key=f"run_saved_{s['name']}"):
                    st.session_state["search_term_val"] = s["search_term"]
                    st.session_state["location_val"] = s["location"]
                    st.session_state["sites_val"] = s["sites"].split(",")
                    st.session_state["remote_val"] = bool(s["is_remote"])
                    st.rerun()
                if sc3.button("Sil", key=f"del_saved_{s['name']}"):
                    delete_saved_search(DB_PATH, s["name"])
                    st.rerun()

    with st.expander("🏢 Şirket Takip Listesi"):
        st.caption("Takip ettiğin şirketler için 'Şimdi Kontrol Et' ile hızlıca yeni ilan arayabilirsin.")
        wc1, wc2 = st.columns([3, 1])
        watch_company = wc1.text_input("Şirket adı", key="watch_company_input")
        if wc2.button("Ekle", key="add_watch_btn"):
            if watch_company.strip():
                add_watched_company(DB_PATH, watch_company.strip(), st.session_state["search_term_val"])
                st.rerun()
        watched = list_watched_companies(DB_PATH) if DB_PATH.parent.exists() else []
        for w in watched:
            wl1, wl2, wl3 = st.columns([3, 1, 1])
            wl1.write(f"**{w['company']}** ({w['search_term']})")
            if wl2.button("Kontrol Et", key=f"check_watch_{w['company']}"):
                with st.spinner(f"{w['company']} için kontrol ediliyor..."):
                    wdf, _ = search_jobs(f"{w['search_term']} {w['company']}", None, ALL_SITES, 10)
                if wdf is not None and not wdf.empty:
                    n = save_jobs(wdf, DB_PATH, try_load_profile())
                    st.success(f"{w['company']}: {n} yeni ilan bulundu ve kaydedildi.")
                else:
                    st.info(f"{w['company']}: sonuç bulunamadı.")
            if wl3.button("Kaldır", key=f"remove_watch_{w['company']}"):
                remove_watched_company(DB_PATH, w["company"])
                st.rerun()

    with st.expander("🕐 Arama Geçmişi"):
        history = list_search_history(DB_PATH) if DB_PATH.parent.exists() else []
        if not history:
            st.caption("Henüz arama yapılmadı.")
        else:
            for h in history[:15]:
                st.caption(f"{h['searched_at'][:16].replace('T', ' ')} — \"{h['search_term']}\" @ {h['location'] or '(her yer)'} → {h['result_count']} sonuç")

    with st.expander("🚫 Şirket & Kelime Kara Listesi (Blacklist)"):
        st.caption("Arama sonuçlarında ve takip listesinde görmek istemediğiniz şirketleri veya anahtar kelimeleri ekleyebilirsiniz.")
        bl_items = get_blacklist(DB_PATH) if DB_PATH.parent.exists() else []
        if bl_items:
            for b in bl_items:
                b_c1, b_c2, b_c3 = st.columns([3, 1, 1])
                kind_badge = "🏢 Şirket" if b["kind"] == "company" else "🔤 Kelime"
                b_c1.write(f"🚫 **{b['keyword']}** ({kind_badge})")
                b_c2.caption(b["created_at"][:10])
                if b_c3.button("Sil", key=f"del_bl_{b['id']}"):
                    remove_from_blacklist(DB_PATH, b["keyword"])
                    st.rerun()
        else:
            st.info("Kara listenizde kayıtlı şirket veya kelime bulunmuyor.")

        st.markdown("##### Yeni Kara Liste Kaydı Ekle")
        nbl_c1, nbl_c2, nbl_c3 = st.columns([3, 2, 1])
        new_bl_kw = nbl_c1.text_input("Şirket adı veya kelime", key="new_bl_kw_input")
        new_bl_kind = nbl_c2.selectbox("Tür", ["company", "keyword"], format_func=lambda x: "Şirket" if x == "company" else "Kelime", key="new_bl_kind_select")
        if nbl_c3.button("Ekle", key="add_bl_btn"):
            if new_bl_kw.strip():
                if add_to_blacklist(DB_PATH, new_bl_kw.strip(), new_bl_kind):
                    st.success(f"'{new_bl_kw.strip()}' kara listeye eklendi.")
                    st.rerun()
                else:
                    st.warning("Bu kayıt zaten kara listede mevcut.")

    with st.form("search_form"):
        c1, c2 = st.columns(2)
        search_term = c1.text_input("Pozisyon / anahtar kelime", key="search_term_val")
        location = c2.text_input("Konum", key="location_val")
        sites = st.multiselect("Platformlar", options=ALL_SITES, key="sites_val")
        c3, c4, c5 = st.columns(3)
        results = c3.number_input("Platform başına sonuç", min_value=1, max_value=50, value=10)
        hours_old = c4.number_input("Son X saat (0 = sınırsız)", min_value=0, value=0)
        country_indeed = c5.text_input("Indeed ülke", value="turkey")
        c6, c7 = st.columns(2)
        remote_only = c6.checkbox("Yalnızca uzaktan çalışma", key="remote_val")
        linkedin_desc = c7.checkbox(
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
                remote_only,
            )
        for site, error in errors:
            st.warning(f"{site} taranamadı: {error}")
        log_search(DB_PATH, search_term, location, sites, 0 if df is None else len(df))
        if df is None or df.empty:
            st.info("Sonuç bulunamadı.")
        else:
            new_count = save_jobs(df, DB_PATH, profile)
            st.success(f"{len(df)} ilan tarandı, {new_count} yeni ilan kaydedildi.")
            show_cols = [
                c for c in ["site", "title", "company", "location", "min_amount", "max_amount", "currency", "is_remote", "job_url"]
                if c in df.columns
            ]
            st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

    with st.expander("💾 Bu aramayı şablon olarak kaydet"):
        template_name = st.text_input("Şablon adı", key="save_search_name")
        if st.button("Kaydet", key="save_search_btn"):
            if template_name.strip():
                save_search(
                    DB_PATH,
                    template_name.strip(),
                    st.session_state["search_term_val"],
                    st.session_state["location_val"],
                    st.session_state["sites_val"],
                    st.session_state["remote_val"],
                )
                st.success(f"'{template_name}' kaydedildi.")
            else:
                st.error("Şablon adı gir.")

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

        with st.expander("📈 Başvuru Analitiği & Dönüşüm Hunisi (Funnel)", expanded=False):
            from app.analytics import get_funnel_metrics, get_platform_distribution, get_score_distribution

            fm = get_funnel_metrics(DB_PATH)
            an_col1, an_col2, an_col3 = st.columns(3)
            an_col1.metric("Başvuru Oranı (Yeni ➔ Başvuruldu)", f"%{fm['applied_rate']}", help="Taranan ilanlardan kaçına başvurulduğu")
            an_col2.metric("Mülakat Dönüş Oranı", f"%{fm['interview_rate']}", help="Başvurulardan mülakata dönüş oranı")
            an_col3.metric("Teklif Oranı", f"%{fm['offer_rate']}", help="Mülakatlardan teklife dönüş oranı")

            st.markdown("##### 🔻 Başvuru Süreç Hunisi")
            f1, f2, f3 = st.columns([1, 1, 1])
            with f1:
                st.write(f"📨 **Başvuruldu:** {fm['applied']} ilan")
                st.progress(min(1.0, fm['applied_rate'] / 100.0) if fm['total'] > 0 else 0.0)
            with f2:
                st.write(f"💼 **Mülakat:** {fm['interview']} görüşme")
                st.progress(min(1.0, fm['interview_rate'] / 100.0) if fm['applied'] > 0 else 0.0)
            with f3:
                st.write(f"🎉 **Teklif:** {fm['offer']} adet")
                st.progress(min(1.0, fm['offer_rate'] / 100.0) if fm['interview'] > 0 else 0.0)

            c_ch1, c_ch2 = st.columns(2)
            with c_ch1:
                st.markdown("##### 🌐 Platform Dağılımı")
                p_dist = get_platform_distribution(DB_PATH)
                if p_dist:
                    st.bar_chart(p_dist)
                else:
                    st.caption("Veri yok.")
            with c_ch2:
                st.markdown("##### 🎯 Eşleşme Skoru Dağılımı")
                s_dist = get_score_distribution(DB_PATH)
                if s_dist:
                    st.bar_chart(s_dist)
                else:
                    st.caption("Veri yok.")

        from app.outreach import check_follow_up_needed
        pending_fu = check_follow_up_needed(DB_PATH, days_threshold=7)
        if pending_fu:
            with st.expander(f"⏳ Takip Zamanı Gelmiş Başvurular ({len(pending_fu)})", expanded=True):
                st.warning(f"**{len(pending_fu)} adet** başvurunuzun üzerinden 7 günden fazla zaman geçti. Nazik bir durum sorgulama e-postası atabilirsiniz.")
                for fu in pending_fu:
                    fu_c1, fu_c2, fu_c3 = st.columns([3, 1, 1])
                    fu_c1.write(f"💼 **{fu['title']}** @ {fu['company']} ({fu['days_elapsed']} gün önce)")
                    fu_c2.caption(f"Tarih: {fu['applied_at']}")
                    if fu_c3.button("Detaya Git", key=f"btn_goto_fu_{fu['job_url']}"):
                        st.session_state["_selected_job_for_tracker"] = fu["job_url"]
                        st.rerun()

        upcoming_interviews = list_upcoming_interviews(DB_PATH, within_days=3) if DB_PATH.exists() else []
        if upcoming_interviews:
            with st.expander(f"🗓️ Yaklaşan Mülakatlar ({len(upcoming_interviews)})", expanded=True):
                st.info("Önümüzdeki 3 gün içinde planlı mülakatların:")
                for iv in upcoming_interviews:
                    st.write(f"📌 **{iv['title']}** @ {iv['company']} — {iv['interview_at']}")

        with st.expander("🔔 Bildirim Ayarları (Telegram / E-posta)"):
            st.caption(
                "Yukarıdaki hatırlatıcıların günlük özetini kendi Telegram botun veya e-posta "
                "hesabın üzerinden gönderebilirsin. Bu uygulama arka planda sürekli çalışmadığı "
                "için gönderim manueldir; otomatik/günlük tekrar için `python -m app.notifications "
                "--telegram-token ... --telegram-chat-id ...` komutunu kendi işletim sisteminin "
                "zamanlayıcısına (cron, Görev Zamanlayıcı) bağlayabilirsin. Bot token/SMTP bilgileri "
                "sana aittir; uygulama bunları saklamaz, yalnızca bu oturumda kullanır."
            )
            from app.notifications import build_daily_digest, send_email_notification, send_telegram_message

            digest_preview = build_daily_digest(DB_PATH) if DB_PATH.exists() else "Henüz veri yok."
            st.text_area("Günlük Özet Önizleme", value=digest_preview, height=150, disabled=True)

            notif_tab_tg, notif_tab_email = st.tabs(["📱 Telegram", "📧 E-posta"])
            with notif_tab_tg:
                tg_token = st.text_input("Telegram Bot Token", type="password", key="notif_tg_token")
                tg_chat_id = st.text_input("Telegram Chat ID", key="notif_tg_chat_id")
                if st.button("Telegram'a Gönder", key="notif_send_tg"):
                    if not tg_token or not tg_chat_id:
                        st.error("Bot token ve chat id gir.")
                    else:
                        try:
                            send_telegram_message(tg_token, tg_chat_id, digest_preview)
                            st.success("Telegram bildirimi gönderildi.")
                        except Exception as exc:
                            st.error(f"Gönderim başarısız: {exc}")
            with notif_tab_email:
                em_host = st.text_input("SMTP Sunucu", placeholder="smtp.gmail.com", key="notif_smtp_host")
                em_port = st.number_input("SMTP Port", value=587, key="notif_smtp_port")
                em_user = st.text_input("SMTP Kullanıcı Adı / E-posta", key="notif_smtp_user")
                em_pass = st.text_input("SMTP Şifre / Uygulama Şifresi", type="password", key="notif_smtp_pass")
                em_to = st.text_input("Alıcı E-posta", key="notif_email_to")
                if st.button("E-posta Gönder", key="notif_send_email"):
                    if not all([em_host, em_user, em_pass, em_to]):
                        st.error("Tüm SMTP alanlarını doldur.")
                    else:
                        try:
                            send_email_notification(
                                em_host, int(em_port), em_user, em_pass, em_to,
                                subject="İş Arama Asistanı — Günlük Özet", body=digest_preview,
                            )
                            st.success("E-posta bildirimi gönderildi.")
                        except Exception as exc:
                            st.error(f"Gönderim başarısız: {exc}")

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
        fc1, fc2, fc3, fc4 = st.columns([2, 1, 1, 1])
        status_filter = fc1.selectbox("Duruma göre filtrele", options=["(hepsi)"] + STATUSES)
        favorite_only = fc2.checkbox("⭐ Yalnızca favoriler")
        filter_remote = fc3.checkbox("🏠 Yalnızca uzaktan")
        filter_bl = fc4.checkbox("🚫 Kara liste gizle", value=True)
        rows = list_jobs(
            DB_PATH,
            limit=200,
            status=None if status_filter == "(hepsi)" else status_filter,
            favorite_only=favorite_only,
            remote_only=filter_remote,
            filter_blacklisted=filter_bl,
        )

        with st.expander("⚖️ Yan Yana İlan Karşılaştırma Aracı (Side-by-Side Compare)"):
            st.caption("Veritabanındaki ilanlardan 2 veya 3 tanesini seçip yan yana yetenek uyumunu, maaşını ve avantajlarını kıyaslayabilirsiniz.")
            all_jobs_for_comp = list_jobs(DB_PATH, limit=100, filter_blacklisted=filter_bl)
            if len(all_jobs_for_comp) < 2:
                st.info("Karşılaştırma yapabilmek için veritabanında en az 2 ilan bulunmalıdır.")
            else:
                comp_options = {f"{j['title']} @ {j['company']} ({j['site'] or ''})": j["job_url"] for j in all_jobs_for_comp}
                selected_for_comp = st.multiselect(
                    "Karşılaştırılacak İlanları Seçin (En fazla 3 ilan)",
                    options=list(comp_options.keys()),
                    max_selections=3,
                    key="comp_multiselect",
                )
                if st.button("Seçili İlanları Kıyasla", key="run_comp_btn", type="primary"):
                    if len(selected_for_comp) < 2:
                        st.warning("Lütfen karşılaştırmak için en az 2 ilan seçin.")
                    else:
                        jobs_to_compare = [dict(get_job(DB_PATH, comp_options[lbl])) for lbl in selected_for_comp if get_job(DB_PATH, comp_options[lbl])]
                        prof = try_load_profile()
                        comp_res = compare_jobs(jobs_to_compare, prof)

                        st.info(comp_res.recommendation)
                        if comp_res.common_skills:
                            st.success(f"🤝 Tüm ilanlarda ortak aranan yetenekleriniz: **{', '.join(comp_res.common_skills)}**")

                        comp_cols = st.columns(len(comp_res.columns))
                        for c_idx, c_data in enumerate(comp_res.columns):
                            with comp_cols[c_idx]:
                                with st.container(border=True):
                                    st.markdown(f"### {c_data.title}")
                                    st.markdown(f"**🏢 {c_data.company}** ({c_data.site})")
                                    st.markdown(f"📍 {c_data.location}")
                                    st.markdown(f"🏠 **Çalışma:** {c_data.is_remote}")
                                    st.markdown(f"💰 **Maaş:** {c_data.salary}")
                                    st.markdown(f"🎯 **Uyum Skoru:** {c_data.match_score}")
                                    st.markdown(f"📌 **Durum:** {c_data.status}")
                                    st.markdown(f"📅 **Tarih:** {c_data.date_posted}")
                                    if c_data.matched_skills:
                                        st.markdown("**✅ Eşleşen Yetenekler:**")
                                        st.caption(", ".join(c_data.matched_skills))
                                    if c_data.missing_skills:
                                        st.markdown("**⚠️ İlanda Olup Profilde Eksik:**")
                                        st.caption(", ".join(c_data.missing_skills))
                                    if c_data.job_url:
                                        st.link_button("İlana Git ↗️", c_data.job_url)
        if not rows:
            st.info("Kayıt bulunamadı.")
        else:
            df = pd.DataFrame([dict(r) for r in rows])
            df["⭐"] = df["favorite"].apply(lambda v: "⭐" if v else "")
            show_cols = [c for c in ["⭐", "title", "company", "site", "location", "min_amount", "max_amount", "currency", "match_score", "status", "job_url"] if c in df.columns]
            st.dataframe(
                df[show_cols],
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
                is_fav = bool(selected_job_data["favorite"])
                c_act1, c_act2, c_act3 = st.columns([1, 1, 2])
                if c_act1.button("💔 Favorilerden Çıkar" if is_fav else "⭐ Favorilere Ekle", key=f"fav_{selected_url}"):
                    toggle_favorite(DB_PATH, selected_url, not is_fav)
                    st.rerun()

                c_act2.link_button("🌐 İlan Sayfası ↗️", selected_url)
                if selected_job_data["status"] == "yeni":
                    if c_act3.button("🚀 Başvuruldu Olarak İşaretle", type="primary", key=f"quick_app_btn_{selected_url}"):
                        set_status(DB_PATH, selected_url, "başvuruldu")
                        st.success("İlan durumu 'Başvuruldu' olarak güncellendi!")
                        st.rerun()

                prof_for_match = try_load_profile()
                if prof_for_match:
                    full_text = f"{selected_job_data['title'] or ''} {selected_job_data['description'] or ''}"
                    matched_kws = get_matched_skills(full_text, prof_for_match)
                    if matched_kws:
                        st.info(f"🎯 Bu ilanla eşleşen yetenekleriniz: **{', '.join(matched_kws)}**")

                    with st.expander("🧠 Bu İlana Özel Mülakat Hazırlığı & Soru Rehberi"):
                        if st.button("Mülakat Rehberi & Soruları Üret", key=f"btn_prep_{selected_url}"):
                            from app.interview_prep import generate_mock_interview

                            with st.spinner("Mülakat stratejisi ve soruları hazırlanıyor..."):
                                prep_res = generate_mock_interview(
                                    prof_for_match,
                                    selected_job_data["title"] or "Uzman",
                                    selected_job_data["company"] or "Şirket",
                                    selected_job_data["description"],
                                    model=model_choice,
                                    api_key=api_key_input or None,
                                )
                            st.session_state[f"prep_{selected_url}"] = prep_res

                        cached_prep = st.session_state.get(f"prep_{selected_url}")
                        if cached_prep:
                            st.markdown("##### ⭐ Öne Çıkarmanız Gereken Güçlü Yönleriniz")
                            for s in cached_prep.key_strengths:
                                st.markdown(f"- {s}")

                            st.markdown("##### ⚠️ Dikkat Edilmesi / Savunulması Gerekenler")
                            for g in cached_prep.potential_gaps:
                                st.markdown(f"- {g}")

                            st.markdown("##### 🎯 Olası Mülakat Soruları & Cevap Taktikleri")
                            for idx, q in enumerate(cached_prep.questions, 1):
                                with st.container(border=True):
                                    st.markdown(f"**{idx}. [{q.category}]** {q.question}")
                                    st.caption(f"🎯 **Neden Sorulur?** {q.rationale}")
                                    st.info(f"💡 **Cevap İpucu:** {q.answer_tip}")

                            if st.button("💾 Soru Bankasına Kaydet", key=f"save_prep_{selected_url}"):
                                save_interview_questions(
                                    DB_PATH,
                                    selected_url,
                                    [q.model_dump() for q in cached_prep.questions],
                                )
                                st.success("Sorular soru bankasına kaydedildi. 'Başvurularım' sekmesinden görüntüleyebilirsin.")

                    with st.expander("✉️ İletişim Şablonları (LinkedIn, Soğuk E-posta, Takip)"):
                        from app.outreach import (
                            generate_cold_email,
                            generate_follow_up_email,
                            generate_linkedin_connection_note,
                            generate_thank_you_email,
                        )

                        recip = st.text_input("Muhatap / Yetkili Adı (opsiyonel)", key=f"recip_{selected_url}")
                        tab_li, tab_cold, tab_fu, tab_ty = st.tabs(
                            ["🔗 LinkedIn Notu", "📧 Soğuk E-posta", "⏳ Takip E-postası", "🤝 Teşekkür Notu"]
                        )

                        with tab_li:
                            li_note = generate_linkedin_connection_note(
                                prof_for_match,
                                selected_job_data["title"] or "Pozisyon",
                                selected_job_data["company"] or "Şirket",
                                recipient_name=recip or None,
                            )
                            st.text_area("LinkedIn Bağlantı Notu (Max 300 Karakter)", value=li_note, height=100)
                            st.caption(f"Karakter sayısı: {len(li_note)} / 300")

                        with tab_cold:
                            sub, body = generate_cold_email(
                                prof_for_match,
                                selected_job_data["title"] or "Pozisyon",
                                selected_job_data["company"] or "Şirket",
                                recipient_name=recip or None,
                            )
                            st.text_input("Konu", value=sub, key=f"cold_sub_{selected_url}")
                            st.text_area("E-posta Gövdesi", value=body, height=220, key=f"cold_body_{selected_url}")

                        with tab_fu:
                            sub_fu, body_fu = generate_follow_up_email(
                                prof_for_match,
                                selected_job_data["title"] or "Pozisyon",
                                selected_job_data["company"] or "Şirket",
                                days_ago=7,
                            )
                            st.text_input("Konu", value=sub_fu, key=f"fu_sub_{selected_url}")
                            st.text_area("E-posta Gövdesi", value=body_fu, height=200, key=f"fu_body_{selected_url}")

                        with tab_ty:
                            sub_ty, body_ty = generate_thank_you_email(
                                prof_for_match,
                                selected_job_data["title"] or "Pozisyon",
                                selected_job_data["company"] or "Şirket",
                                interviewer_name=recip or None,
                            )
                            st.text_input("Konu", value=sub_ty, key=f"ty_sub_{selected_url}")
                            st.text_area("E-posta Gövdesi", value=body_ty, height=200, key=f"ty_body_{selected_url}")

                    with st.expander("💰 Maaş Beklentisi & Pazarlık Rehberi"):
                        from app.salary_estimator import estimate_salary

                        sal_col1, sal_col2, sal_col3 = st.columns(3)
                        role_val = sal_col1.text_input("Rol / Pozisyon", value=selected_job_data["title"] or "Yazılım Geliştirici", key=f"sal_r_{selected_url}")
                        exp_val = sal_col2.selectbox("Deneyim Seviyesi", ["junior", "mid", "senior", "lead"], index=1, format_func=lambda x: {"junior": "Junior (0-2 Yıl)", "mid": "Mid-Level (2-5 Yıl)", "senior": "Senior (5-8 Yıl)", "lead": "Lead / Staff (8+ Yıl)"}[x], key=f"sal_e_{selected_url}")
                        curr_val = sal_col3.selectbox("Para Birimi", ["TRY", "USD", "EUR"], index=0, key=f"sal_c_{selected_url}")

                        sal_res = estimate_salary(role_val, experience_level=exp_val, location=selected_job_data["location"] or "istanbul", currency=curr_val)

                        m_c1, m_c2, m_c3 = st.columns(3)
                        m_c1.metric("Tahmini Minimum", f"{sal_res.min_monthly:,.0f} {sal_res.currency} / ay")
                        m_c2.metric("Piyasa Ortancası", f"{sal_res.median_monthly:,.0f} {sal_res.currency} / ay")
                        m_c3.metric("Tahmini Üst Bant", f"{sal_res.max_monthly:,.0f} {sal_res.currency} / ay")

                        st.caption(f"Yıllık eşdeğer: {sal_res.min_annual:,.0f} - {sal_res.max_annual:,.0f} {sal_res.currency}")
                        st.info(sal_res.market_insights)

                        st.markdown("**🗣️ Mülakatta Kullanabileceğiniz Pazarlık Cümleleri:**")
                        for tp in sal_res.talking_points:
                            st.write(f"- *\"{tp}\"*")

                        st.markdown("**💡 Pazarlık İpuçları & Stratejiler:**")
                        for tip in sal_res.negotiation_tips:
                            st.caption(f"• {tip}")



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
                        ics_col1, ics_col2 = st.columns([1, 1])
                        ics_col1.download_button(
                            "📅 Takvim Dosyasını İndir (.ics)",
                            data=ics_content,
                            file_name=f"mulakat_{(selected_job_data['company'] or 'etkinlik').replace(' ', '_')}.ics",
                            mime="text/calendar",
                        )
                        if ics_col2.button("🔔 Hatırlatıcı Olarak Kaydet", key=f"save_interview_{selected_url}"):
                            set_interview_datetime(DB_PATH, selected_url, dt_start.isoformat())
                            st.success("Mülakat tarihi kaydedildi. 'Bildirimler' bölümünde hatırlatılacak.")

            if st.button("Güncelle"):
                job_url = options[selected_label]
                set_status(DB_PATH, job_url, new_status, notes or None)
                st.success("Güncellendi.")
                st.rerun()

        st.divider()
        with st.expander("📚 Kişisel Mülakat Soru Bankası"):
            st.caption(
                "'İş Ara' sekmesindeki mülakat hazırlığından kaydettiğin tüm sorular "
                "burada birikir. Her soruya kendi cevabını yazıp saklayabilirsin."
            )
            qb_all_jobs = list_jobs(DB_PATH, limit=200) if DB_PATH.exists() else []
            qb_options = {f"{r['title']} — {r['company']}": r["job_url"] for r in qb_all_jobs}
            qb_job_filter = st.selectbox(
                "İlana göre filtrele",
                options=["(tümü)"] + list(qb_options.keys()),
                key="qb_job_filter",
            )
            filter_job_url = None if qb_job_filter == "(tümü)" else qb_options.get(qb_job_filter)
            bank_questions = list_interview_questions(DB_PATH, job_url=filter_job_url) if DB_PATH.exists() else []
            if not bank_questions:
                st.info("Soru bankası boş. 'İş Ara' sekmesinden bir ilan için mülakat rehberi üretip kaydedebilirsin.")
            else:
                for bq in bank_questions:
                    bq_job = get_job(DB_PATH, bq["job_url"]) if bq["job_url"] else None
                    job_label = f"{bq_job['title']} — {bq_job['company']}" if bq_job else "Genel"
                    with st.container(border=True):
                        st.caption(f"📌 {job_label}  ·  [{bq['category'] or ''}]")
                        st.markdown(f"**{bq['question']}**")
                        if bq["rationale"]:
                            st.caption(f"🎯 {bq['rationale']}")
                        if bq["answer_tip"]:
                            st.caption(f"💡 {bq['answer_tip']}")
                        personal_answer = st.text_area(
                            "Kendi cevabım",
                            value=bq["personal_answer"] or "",
                            key=f"qb_answer_{bq['id']}",
                            height=80,
                        )
                        qb_col1, qb_col2 = st.columns([1, 1])
                        if qb_col1.button("Cevabı Kaydet", key=f"qb_save_{bq['id']}"):
                            update_interview_answer(DB_PATH, bq["id"], personal_answer)
                            st.success("Cevap kaydedildi.")
                        if qb_col2.button("Sil", key=f"qb_delete_{bq['id']}"):
                            delete_interview_question(DB_PATH, bq["id"])
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
        letter_language = st.radio("Dil", options=["Türkçe", "İngilizce"], horizontal=True, key="letter_language")
        if st.button("Taslak Oluştur", type="primary"):
            if not company:
                st.error("Şirket adını gir.")
            elif letter_language == "İngilizce":
                try:
                    with st.spinner("İngilizce taslak yapay zeka ile hazırlanıyor..."):
                        letter = generate_cover_letter_english(
                            profile,
                            job_title,
                            company,
                            job_description or None,
                            provider=provider_choice,
                            model=model_choice,
                            api_key=api_key_input or None,
                        )
                    st.session_state["cover_letter_text"] = letter
                except Exception as exc:
                    st.error(f"İngilizce taslak oluşturulamadı: {exc}")
            else:
                letter = generate_cover_letter(profile, job_title, company, job_description or None)
                st.session_state["cover_letter_text"] = letter
        if "cover_letter_text" in st.session_state:
            edited = st.text_area("Taslak (düzenlenebilir)", value=st.session_state["cover_letter_text"], height=300)
            lt_col1, lt_col2, lt_col3 = st.columns([1, 1, 1])
            lt_col1.download_button("Metni indir (.txt)", data=edited, file_name="on_yazi.txt", mime="text/plain")
            letter_theme = lt_col2.selectbox(
                "Kurumsal Antet Teması",
                options=list(THEMES.keys()),
                format_func=lambda k: THEMES[k]["name"],
                key="letter_theme_choice",
            )
            pdf_bytes = bytes(render_letter_pdf(edited, profile=profile, theme=letter_theme).output())
            lt_col3.download_button(
                "Kurumsal PDF olarak indir",
                data=pdf_bytes,
                file_name=f"{profile.contact.full_name.replace(' ', '_')}_On_Yazi.pdf",
                mime="application/pdf",
            )

        st.divider()
        with st.expander("📨 Toplu Ön Yazı Üretimi"):
            st.caption("Kayıtlı ilanlardan birden fazlasını seçip hepsi için tek seferde ön yazı taslağı üret.")
            if not DB_PATH.exists():
                st.info("Henüz kayıtlı ilan yok. Önce 'İş Ara' sekmesinden ilan kaydet.")
            else:
                bulk_rows = list_jobs(DB_PATH, limit=200)
                if len(bulk_rows) < 2:
                    st.info("Toplu üretim için en az 2 kayıtlı ilan gerekir.")
                else:
                    bulk_options = {f"{r['title']} — {r['company']}": r["job_url"] for r in bulk_rows}
                    bulk_selected = st.multiselect(
                        "İlanları seç",
                        options=list(bulk_options.keys()),
                        key="bulk_letter_select",
                    )
                    bulk_language = st.radio(
                        "Dil", options=["Türkçe", "İngilizce"], horizontal=True, key="bulk_letter_language"
                    )
                    if st.button("Seçili İlanlar İçin Taslaklar Üret", key="bulk_letter_generate_btn"):
                        if not bulk_selected:
                            st.warning("En az bir ilan seç.")
                        else:
                            bulk_jobs = [dict(get_job(DB_PATH, bulk_options[lbl])) for lbl in bulk_selected]
                            try:
                                with st.spinner(f"{len(bulk_jobs)} ilan için taslaklar hazırlanıyor..."):
                                    bulk_letters = generate_bulk_cover_letters(
                                        profile,
                                        bulk_jobs,
                                        language="en" if bulk_language == "İngilizce" else "tr",
                                        provider=provider_choice,
                                        model=model_choice,
                                        api_key=api_key_input or None,
                                    )
                                st.session_state["bulk_cover_letters"] = bulk_letters
                            except Exception as exc:
                                st.error(f"Toplu üretim başarısız: {exc}")

                    if st.session_state.get("bulk_cover_letters"):
                        import io
                        import zipfile

                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            for job_url, letter_text in st.session_state["bulk_cover_letters"].items():
                                job = get_job(DB_PATH, job_url)
                                fname = f"{(job['company'] if job else 'ilan').replace(' ', '_')}_on_yazi.txt"
                                zf.writestr(fname, letter_text)
                        st.download_button(
                            "📦 Tüm Taslakları ZIP Olarak İndir",
                            data=zip_buffer.getvalue(),
                            file_name="toplu_on_yazilar.zip",
                            mime="application/zip",
                            key="bulk_letter_zip_dl",
                        )
                        for job_url, letter_text in st.session_state["bulk_cover_letters"].items():
                            job = get_job(DB_PATH, job_url)
                            label = f"{job['title']} — {job['company']}" if job else job_url
                            with st.expander(label):
                                st.text(letter_text)
