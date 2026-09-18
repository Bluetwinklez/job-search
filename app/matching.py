"""Metin içinde anahtar kelime/yetenek eşleşmesi için ortak yardımcılar."""

from __future__ import annotations

import re

STOPWORDS = {
    "ve", "ile", "bir", "bu", "de", "da", "için", "olan", "gibi", "çok",
    "the", "and", "for", "with", "our", "you", "are", "your",
}

_TR_LOWER_MAP = str.maketrans({
    "İ": "i",
    "I": "ı",
})


def turkish_lower(text: str) -> str:
    """Türkçe İ/I karakterlerini standart küçük harfe dönüştürür."""
    if not text:
        return ""
    return text.translate(_TR_LOWER_MAP).lower()


def contains_keyword(text: str, keyword: str) -> bool:
    """`keyword`nun `text` içinde tam kelime/öbek olarak geçip geçmediğini döner (Türkçe uyumlu)."""
    if not text or not keyword:
        return False
    norm_text = turkish_lower(text)
    norm_kw = turkish_lower(keyword)
    return re.search(rf"(?<!\w){re.escape(norm_kw)}(?!\w)", norm_text) is not None


def split_keywords(phrase: str) -> set[str]:
    """Çok kelimeli bir ifadeyi (ör. 'Reçete karşılama') anlamlı tekil kelimelere ayırır.

    Bu, ifadenin tamamı bir metinde birebir geçmese bile ("reçete karşılama
    süreci" gibi bir varyasyon geçtiğinde) kısmi eşleşme sağlamak için kullanılır.
    """
    if not phrase:
        return set()
    norm_phrase = turkish_lower(phrase)
    words = {w.strip(".,;:()/\\-") for w in norm_phrase.split()}
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}


def extract_matching_keywords(text: str, keywords: set[str] | list[str]) -> list[str]:
    """Metin içinde geçen anahtar kelimeleri tespit edip liste olarak döner."""
    if not text or not keywords:
        return []
    return [kw for kw in keywords if contains_keyword(text, kw)]

