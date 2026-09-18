"""Modern UI/UX tema, tipografi ve stil motoru."""

from __future__ import annotations

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.01em;
}

/* Metrik Kartları — Modern Glassmorphism & Hover */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(128, 128, 128, 0.15);
    border-radius: 12px;
    padding: 12px 18px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    border-color: rgba(99, 102, 241, 0.5);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
}

/* Kanban & Konteyner Kartları */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border: 1px solid rgba(128, 128, 128, 0.18) !important;
    background: rgba(128, 128, 128, 0.02);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(99, 102, 241, 0.4) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
    transform: translateY(-1px);
}

/* Butonlar — Gradient & Micro-interaction */
button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
    transition: all 0.2s ease !important;
}

button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5) !important;
}

button[kind="secondary"] {
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

button[kind="secondary"]:hover {
    transform: translateY(-1px) !important;
}

/* Sekmeler (Tabs) */
div[data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid rgba(128, 128, 128, 0.2);
    padding-bottom: 6px;
}

div[data-baseweb="tab"] {
    border-radius: 8px 8px 0 0 !important;
    padding: 8px 16px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease;
}

/* Expander Başlıkları */
div[data-testid="stExpander"] details summary {
    font-weight: 600;
    border-radius: 8px;
    transition: background-color 0.2s ease;
}

/* Mobil & Tablet Uyumlu Düzenlemeler */
@media (max-width: 768px) {
    div[data-testid="stMetric"] {
        padding: 8px 12px;
    }
    div[data-baseweb="tab"] {
        padding: 6px 10px !important;
        font-size: 0.85rem !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 2px;
        overflow-x: auto;
        flex-wrap: nowrap;
    }
    /* Yan yana sütunları dikey akışa çevir (form/karşılaştırma alanları hariç,
       Streamlit bunu kısmen kendisi yapar; burada boşlukları sıkılaştırıyoruz) */
    div[data-testid="stHorizontalBlock"] {
        gap: 0.6rem;
    }
    div[data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1.5rem !important;
    }
    /* Dokunmatik ekranlarda daha rahat tıklanabilir butonlar */
    button {
        min-height: 42px;
    }
    div[data-testid="stDataFrame"] {
        font-size: 0.85rem;
    }
}
</style>
"""


def apply_theme() -> None:
    """Streamlit arayüzüne modern tema ve stil tanımlarını enjekte eder."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
