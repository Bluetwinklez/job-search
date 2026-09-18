"""Profili İngilizceye çevirir (Claude API ile, structured output).

`app.cv_rewrite` ile aynı ilkeyi izler: model yeni bilgi UYDURMAZ, yalnızca
var olan metin alanlarını (özet, deneyim maddeleri, unvanlar, dereceler vb.)
doğal İngilizceye çevirir. Sayılar, tarihler, şirket/okul adları ve iletişim
bilgileri olduğu gibi korunur.

Kullanım:
    python -m app.cv_translate --profile data/profile.json --output data/profile_en.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models import Profile

DEFAULT_MODEL = "claude-opus-5"

TRANSLATE_INSTRUCTIONS = """\
Aşağıda JSON formatında bir CV/özgeçmiş profili var. Bu profildeki TÜM
doğal dil metin alanlarını (unvan, özet, deneyim rolleri/highlights,
eğitim derece/alan adları, proje açıklamaları vb.) doğal, profesyonel
İngilizceye çevir.

Kurallar:
- Yeni bilgi, deneyim, başarı veya beceri UYDURMA — yalnızca çeviri yap.
- Kişi adı, şirket/okul adı, e-posta, telefon, linkedin/github/website gibi
  özel adları ve iletişim bilgilerini OLDUĞU GİBİ koru (çevirme).
- Tarihleri (start_date, end_date) ve sayısal verileri olduğu gibi koru.
- Teknoloji/araç adlarını (tech_stack, technologies, skills.items) genellikle
  değiştirme (örn. "Python", "Docker" zaten İngilizce) ama Türkçe beceri
  kategorisi adlarını (skills.category, örn. "Diller" -> "Languages") çevir.
- "Halen" gibi bir bitiş ifadesi kullanılmışsa bunu None/boş bırak, uydurma.

PROFİL JSON:
---
{profile_json}
---
"""


def translate_profile_to_english(profile: Profile, model: str = DEFAULT_MODEL, api_key: str | None = None) -> Profile:
    import os

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY ortam değişkeni tanımlı değil. Lütfen geçerli bir Anthropic API anahtarı sağlayın."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    parse_fn = getattr(client.beta.messages, "parse", None) if hasattr(client, "beta") else None
    if parse_fn is None:
        parse_fn = getattr(client.messages, "parse", None)
    if parse_fn is None:
        raise RuntimeError("Yüklü anthropic kütüphanesi structured output (.parse) desteklemiyor. Lütfen güncelleyin.")

    profile_json = json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)
    response = parse_fn(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": TRANSLATE_INSTRUCTIONS.format(profile_json=profile_json)}],
        output_format=Profile,
    )
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Profili İngilizceye çevirir.")
    parser.add_argument("--profile", type=Path, required=True, help="Profil JSON dosyası yolu")
    parser.add_argument("--output", type=Path, default=Path("data/profile_en.json"), help="Çıktı JSON yolu")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    data = json.loads(args.profile.read_text(encoding="utf-8"))
    profile = Profile.model_validate(data)
    translated = translate_profile_to_english(profile, model=args.model)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(translated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"İngilizce profil kaydedildi: {args.output}")


if __name__ == "__main__":
    main()
