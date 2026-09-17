"""Metin içinde anahtar kelime/yetenek eşleşmesi için ortak yardımcılar."""

from __future__ import annotations

import re


def contains_keyword(text: str, keyword: str) -> bool:
    """`keyword`nun `text` içinde tam kelime/öbek olarak geçip geçmediğini döner."""
    return re.search(rf"(?<!\w){re.escape(keyword.lower())}(?!\w)", text.lower()) is not None
