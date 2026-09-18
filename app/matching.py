"""Metin içinde anahtar kelime/yetenek eşleşmesi için ortak yardımcılar."""

from __future__ import annotations

import re

STOPWORDS = {
    "ve", "ile", "bir", "bu", "de", "da", "için", "olan", "gibi", "çok",
    "the", "and", "for", "with", "our", "you", "are", "your",
}


def contains_keyword(text: str, keyword: str) -> bool:
    """`keyword`nun `text` içinde tam kelime/öbek olarak geçip geçmediğini döner."""
    return re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", text.lower()) is not None


def split_keywords(phrase: str) -> set[str]:
    """Çok kelimeli bir ifadeyi (ör. 'Reçete karşılama') anlamlı tekil kelimelere ayırır.

    Bu, ifadenin tamamı bir metinde birebir geçmese bile ("reçete karşılama
    süreci" gibi bir varyasyon geçtiğinde) kısmi eşleşme sağlamak için kullanılır.
    """
    words = {w.strip(".,;:()/\\-").lower() for w in phrase.split()}
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}
