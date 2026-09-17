"""Var olan (ham) bir CV metnini ATS-dostu, yapılandırılmış bir profile
yeniden yazar (Claude API ile).

Kullanıcı elindeki mevcut CV'yi (PDF'ten kopyaladığı düz metin, Word'den
yapıştırdığı metin vb.) verir; Claude bunu `app.models.Profile` şemasına
uygun, işe alım uzmanının ve ATS yazılımının olumlu değerlendireceği
şekilde yeniden yazılmış bir profile dönüştürür. Sonuç doğrudan
`app.cv_generator.build_cv` ile ATS-dostu PDF'e çevrilebilir veya
`data/profile.json` olarak kaydedilip uygulamanın geri kalanında
(iş arama eşleşmesi, ön yazı, ilana özel uyarlama) kullanılabilir.

Önemli: model yeni deneyim/başarı/şirket UYDURMAZ — yalnızca CV
metninde zaten var olan bilgileri daha güçlü, somut ve ATS-dostu bir
dille yeniden ifade eder ve mantıklı kategorilere ayırır.

Kullanım:
    python -m app.cv_rewrite --input ham_cv.txt --output data/profile.json \\
        --pdf cv_yeniden_yazilmis.pdf

ANTHROPIC_API_KEY ortam değişkeninin (veya `ant auth login` ile
kaydedilmiş bir profilin) tanımlı olması gerekir.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models import Profile

DEFAULT_MODEL = "claude-opus-5"

REWRITE_INSTRUCTIONS = """\
Aşağıda bir adayın ham/düzensiz CV metni var. Bunu, verilen şemaya uygun,
ATS (başvuru takip sistemi) tarafından hatasız ayrıştırılacak ve işe alım
uzmanı tarafından olumlu değerlendirilecek şekilde YENİDEN YAZILMIŞ bir
profile dönüştür.

Kurallar:
- Yalnızca metinde geçen gerçek bilgileri kullan. Yeni şirket, unvan, tarih,
  proje veya başarı UYDURMA. Emin olmadığın bir alanı boş bırak.
- Deneyim maddelerini (highlights) somut/ölçülebilir bir dille yeniden yaz:
  metinde sayısal bir veri (%, adet, süre vb.) varsa vurgula; yoksa uydurma,
  sadece daha güçlü ve net fiillerle ifade et (ör. "sorumluydu" yerine
  "yönetti", "geliştirdi", "azalttı" gibi).
- Özeti (summary), jenerik ifadelerden ("takım oyuncusu", "sonuç odaklı")
  kaçınarak adayın gerçek uzmanlık alanına odaklanan 2-4 cümlelik bir CV
  özeti olarak yaz.
- Yetenekleri mantıklı kategorilere ayır (ör. "Diller", "Araçlar",
  "Yazılımlar" — CV'nin alanına uygun kategori adları kullan).
- İletişim bilgilerini (ad, güncel/en son unvan, e-posta, telefon, konum,
  varsa linkedin/github/website) metinden eksiksiz çıkar. E-posta metinde
  yoksa bu alanı olabildiğince metindeki haliyle doldur; hiç yoksa boş
  bırakma çünkü zorunlu bir alan — böyle bir durumda metinde geçen ilk
  iletişim bilgisini (varsa) kullan.

HAM CV METNİ:
---
{raw_cv}
---
"""


def rewrite_cv(raw_cv_text: str, model: str = DEFAULT_MODEL) -> Profile:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": REWRITE_INSTRUCTIONS.format(raw_cv=raw_cv_text)}],
        output_format=Profile,
    )
    return response.parsed_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Ham bir CV metnini ATS-dostu yapılandırılmış profile dönüştürür.")
    parser.add_argument("--input", type=Path, required=True, help="Ham CV metnini içeren dosya")
    parser.add_argument("--output", type=Path, default=Path("data/profile.json"), help="Yazılacak profil JSON dosyası")
    parser.add_argument("--pdf", type=Path, default=None, help="Verilirse, yeniden yazılan profilden PDF CV de üretir")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    raw_cv_text = args.input.read_text(encoding="utf-8")
    profile = rewrite_cv(raw_cv_text, args.model)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Yeniden yazılmış profil kaydedildi: {args.output}")

    if args.pdf:
        from app.cv_generator import build_cv

        pdf = build_cv(profile)
        pdf.output(str(args.pdf))
        print(f"PDF CV oluşturuldu: {args.pdf}")


if __name__ == "__main__":
    main()
