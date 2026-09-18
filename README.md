# İş Arama Asistanı

Tek bir profilden başlayıp iş arama sürecinin tamamını kapsayan bir araç
seti: **ATS-dostu CV oluşturma**, **çoklu platformdan iş ilanı tarama**,
**başvuru takibi**, **ön yazı taslağı** ve (Claude API ile) **ilana özel
CV uyarlama / var olan CV'yi yeniden yazma**. Hepsi tek bir web
arayüzünden ya da ayrı ayrı komut satırı araçlarından kullanılabilir.

## Hızlı Başlangıç

```bash
pip install -r requirements.txt
cp data/profile.example.json data/profile.json   # kendi bilgilerinle doldur
streamlit run streamlit_app.py
```

Tarayıcıda `http://localhost:8501` açılır. Beş sekme: **Profil**, **CV
Oluştur**, **İş Ara**, **Başvurularım**, **Ön Yazı**.

## Özellikler

| Özellik | Modül | LLM gerekli mi? |
|---|---|---|
| ATS-dostu PDF CV üretimi (Projeler & Sertifikalar dahil) | `app/cv_generator.py` | Hayır |
| Çoklu platformdan iş ilanı tarama (LinkedIn, Indeed, Glassdoor, Google, vb.) | `app/job_search.py` | Hayır |
| İlan / profil eşleşme skoru & analiz | `app/job_search.py`, `app/matching.py` | Hayır |
| Başvuru CRM'i & Kanban Panosu | `streamlit_app.py`, `app/tracker.py` | Hayır |
| Mülakat takvimi entegrasyonu (.ics indir) | `app/calendar_export.py` | Hayır |
| AI Mülakat Hazırlık Asistanı & Soru Rehberi | `app/interview_prep.py` | Opsiyonel (kural tabanlı fallback) |
| Ağ & İletişim Şablonları (LinkedIn, Soğuk E-posta, Takip) | `app/outreach.py` | Hayır |
| İlana özel ön yazı taslağı (PDF/metin) | `app/cover_letter.py` | Hayır |
| İlana özel CV uyarlama | `app/cv_tailor.py` | Evet (Claude API) |
| Var olan bir CV'yi ATS-dostu yeniden yazma | `app/cv_rewrite.py` | Evet (Claude API) |
| Web arayüzü (hepsini birleştirir) | `streamlit_app.py` | — |
| Windows tek tıkla masaüstü başlatıcı | `baslat.bat` | — |

Claude API gerektiren özellikler için kenar çubuğundan (Sidebar) veya ortamdan `ANTHROPIC_API_KEY` girilebilir; diğer tüm özellikler anahtarsız doğrudan çalışır.

## Proje Yapısı

```
app/
  models.py           # Merkezi profil şeması (Pydantic: Deneyim, Eğitim, Sertifika, Proje)
  cv_generator.py      # Profilden ATS-dostu PDF CV üretimi
  job_search.py        # Çoklu platform iş ilanı tarama + SQLite kayıt + akıllı eşleşme
  tracker.py           # Başvuru durumu takip CLI'ı
  calendar_export.py   # Mülakatlar için RFC 5545 iCalendar (.ics) takvim üretici
  interview_prep.py    # İlana ve profile özel mülakat soruları ve hazırlık asistanı
  outreach.py          # LinkedIn 300 karakter notu, soğuk e-posta, takip & teşekkür şablonları
  cover_letter.py       # Ön yazı taslağı üretimi (metin + PDF)
  cv_tailor.py          # İlana özel CV uyarlama (Claude API)
  cv_rewrite.py         # Var olan CV'yi ATS-dostu yeniden yazma (Claude API)
  matching.py           # Türkçe karakter uyumlu anahtar kelime eşleştirme
data/
  profile.example.json  # Örnek profil
  profile.json          # Kendi profilin (git'e girmez, .gitignore'da)
  jobs.db              # Taranan ilanlar ve CRM veritabanı (git'e girmez)
assets/fonts/          # PDF'lerde Türkçe karakter desteği için DejaVu fontları
tests/                 # 23 adet otomatik birim testi
baslat.bat             # Windows için tek tıkla başlatan masaüstü aracı
streamlit_app.py        # Tüm özellikleri birleştiren modern web arayüzü
```

## 1. CV Oluşturma

Amaç: standart, tek sütunlu, tablosuz/ikonsuz bir CV — bu format hem ATS
yazılımları tarafından hatasız ayrıştırılır hem de işe alım uzmanlarının
hızlıca tarayabileceği sade bir okunabilirlik sağlar. Bölüm başlıkları
ve vurgu renkleri sade bir görsel kimlik verir; grafik veya metin içeren
görsel kullanılmaz (ATS uyumluluğunu bozar).

1. `data/profile.example.json` dosyasını kopyalayıp kendi bilgilerinle doldur:

   ```bash
   cp data/profile.example.json data/profile.json
   ```

2. PDF CV oluştur:

   ```bash
   python -m app.cv_generator --profile data/profile.json --output cv.pdf
   ```

### Profil Şeması

Profil dosyası şu bölümlerden oluşur: `contact` (iletişim bilgileri),
`summary` (özet), `experience` (iş deneyimi), `education` (eğitim),
`skills` (yetenek grupları), `languages` (dil bilgisi). Alan tanımları
için `app/models.py` içindeki Pydantic modellerine bakabilirsin.

### ATS ve işe alım uzmanı için öneriler

- Deneyim maddelerini somut sonuçla yaz ("sorumluydu" yerine "%40 azalttı",
  "3 kişilik ekibi yönetti" gibi ölçülebilir ifadeler kullan).
- İlana özgü anahtar kelimeleri (teknoloji adları, unvan) `tech_stack` ve
  `skills` alanlarına ilanla aynı yazımla ekle — ATS sistemleri genelde
  birebir eşleşme arar.
- Özet (summary) bölümünü jenerik ifadelerden ("takım oyuncusu",
  "sonuç odaklı") kaçınarak somut uzmanlık alanına göre yaz.
- CV'yi tek sayfada tutmaya çalış (2-3 deneyimden fazlaysa en alakalı
  olanları öne al).

## 2. İş İlanı Arama

```bash
python -m app.job_search \
  --search-term "Backend Developer" \
  --location "Istanbul, Turkey" \
  --results 20 \
  --profile data/profile.json
```

Varsayılan olarak tüm platformlar (`linkedin,indeed,glassdoor,google,zip_recruiter,bayt,naukri`)
taranır; `--sites linkedin,indeed` gibi bir alt küme de verilebilir. Her
platform kendi izole thread'inde paralel taranır: bir platform o ülke/
sorgu için desteklenmiyorsa (ör. Glassdoor bazı ülkelerde çalışmaz)
yalnızca o platform atlanır, uyarı basılır ve diğer platformlardan gelen
sonuçlar yine de kaydedilir — hiçbir sonuç gereksiz yere tekrar taranmaz.

Sonuçlar `data/jobs.db` (SQLite) içine tekilleştirilerek kaydedilir;
`--profile` verilirse her ilan için profildeki yetenek/teknoloji
anahtar kelimeleriyle bir eşleşme skoru (0-1) hesaplanır. Skor hem tam
ifadeleri (ör. "Python") hem de çok kelimeli ifadelerin ("Reçete
karşılama" gibi) tekil kelimelerini dikkate alır — böylece teknik
olmayan/Türkçe yetenek listelerinde de anlamlı bir skor üretilir.

Diğer parametreler:

- `--hours-old 24` — yalnızca son 24 saatte açılan ilanlar
- `--country-indeed turkey` — Indeed'in ülke bazlı sonuçları için (varsayılan `turkey`)
- `--linkedin-descriptions` — LinkedIn ilanları için de açıklama metnini çek (eşleşme skoru hesaplanabilsin diye; her ilan için ekstra istek attığı için daha yavaştır)
- `--db data/jobs.db` — kayıtların tutulacağı SQLite dosyası

**Not:** Tarama, ilgili sitelerin herkese açık iş ilanı sonuçlarını
kullanır ([JobSpy](https://github.com/speedyapply/JobSpy) kütüphanesi
üzerinden). Sık/yüksek hacimli istek atmak ilgili sitenin kullanım
koşullarını ihlal edebilir ve IP engellemesine yol açabilir; `--results`
değerini makul tut ve gereğinden sık çalıştırma.

## 3. Başvuru Takibi

Taranan ilanların durumunu (`yeni`, `başvuruldu`, `mülakat`, `reddedildi`,
`teklif`) yönetir. `--db` alt komuttan önce verilmelidir.

```bash
python -m app.tracker list --status başvuruldu
python -m app.tracker --db data/jobs.db set "<job_url>" mülakat --notes "Teknik mülakat 25 Eylül"
python -m app.tracker stats
```

`stats` komutu toplam başvuru sayısı ve geri dönüş oranını (mülakat +
reddedildi + teklif / başvuruldu ve sonrası) gösterir.

## 4. Ön Yazı Taslağı

LLM gerektirmez: profildeki özet, ilana **en alakalı** deneyim (ilan
başlığı/açıklamasıyla ortak anahtar kelimelere göre otomatik seçilir) ve
eşleşen yetenekleri birleştirip düzenlenebilir bir taslak üretir. Hem
düz metin hem de PDF çıktısı alınabilir.

```bash
python -m app.cover_letter \
  --profile data/profile.json \
  --title "Backend Developer" \
  --company "Acme Tech" \
  --job-description-file ilan.txt \
  --output cover_letter.txt \
  --pdf cover_letter.pdf
```

Web arayüzünde **Ön Yazı** sekmesinde, `data/jobs.db`'ye kaydedilmiş bir
ilanı seçip alanları otomatik doldurabilir, taslağı düzenleyip hem
`.txt` hem `.pdf` olarak indirebilirsin.

## 5. İlana Özel CV Uyarlama (Claude API ile)

Bir ilan açıklaması verildiğinde Claude, profildeki **gerçekleri değiştirmeden**
yalnızca şunlara karar verir: (a) bu ilana özel kısa bir özet metni, (b) her
deneyimdeki maddelerin/teknolojilerin ve yetenek listelerinin ilanla alaka
düzeyine göre yeniden sıralanması. Yeni bir deneyim, yetenek ya da başarı
uydurulmaz — model yalnızca var olanlar arasından öne çıkarılacakları seçer,
ardından sonuç `app.cv_generator.build_cv` ile aynı ATS-dostu PDF'e dönüştürülür.
Ayrıca ilanda geçip profilde bulunmayan anahtar kelimeler ayrıca listelenir.

Çalışması için ortamda `ANTHROPIC_API_KEY` tanımlı olmalı (veya `ant auth login`
ile kaydedilmiş bir profil).

```bash
python -m app.cv_tailor \
  --profile data/profile.json \
  --job-description-file ilan.txt \
  --output cv_tailored.pdf
```

Web arayüzünde bu özelliğe **CV Oluştur** sekmesindeki "İlana özel uyarla
(Claude ile)" bölümünden erişilebilir.

## 6. Var Olan Bir CV'yi Yeniden Yazma (Claude API ile)

Elindeki mevcut bir CV'yi (PDF'ten kopyaladığın düz metin ya da `.txt`/`.pdf`
dosyası) verirsin; Claude bunu `app.models.Profile` şemasına uygun, ATS
tarafından hatasız ayrıştırılacak ve işe alım uzmanının olumlu
değerlendireceği şekilde yeniden yazılmış bir profile dönüştürür. Yeni
deneyim/başarı/şirket **uydurulmaz** — yalnızca CV'de zaten var olan
bilgiler daha güçlü, somut bir dille yeniden ifade edilir ve mantıklı
kategorilere ayrılır.

Çalışması için ortamda `ANTHROPIC_API_KEY` tanımlı olmalı.

```bash
python -m app.cv_rewrite \
  --input ham_cv.txt \
  --output data/profile.json \
  --pdf cv_yeniden_yazilmis.pdf
```

Web arayüzünde **Profil** sekmesindeki "Var olan bir CV'yi yükle ve
yeniden yaz (Claude ile)" bölümünden `.pdf`/`.txt` yükleyebilir ya da
metni doğrudan yapıştırabilirsin; sonuç profil düzenleyicisine
otomatik doldurulur, incelendikten sonra "Kaydet"e basman yeterli.

## 7. İngilizce CV (Claude API ile)

`app/cv_translate.py`, profildeki gerçek bilgileri koruyarak (yeni bilgi
uydurmadan) tüm metin alanlarını doğal İngilizceye çevirir; şirket/okul
adları, tarihler ve iletişim bilgileri değiştirilmez. Sonuç, İngilizce
bölüm başlıklarıyla (`Summary`, `Experience`, `Education`, ...) PDF CV
üretiminde kullanılır.

Çalışması için ortamda `ANTHROPIC_API_KEY` tanımlı olmalı.

```bash
python -m app.cv_translate --profile data/profile.json --output data/profile_en.json
python -m app.cv_generator --profile data/profile_en.json --output cv_en.pdf --language en
```

Web arayüzünde **CV Oluştur** sekmesindeki "🌐 İngilizce CV Oluştur"
bölümünden tek tıkla üretilebilir. Aynı çeviri prensibi Ön Yazı
sekmesindeki dil seçeneğinde de kullanılır (bkz. bölüm 4).

## Not: LinkedIn'den Otomatik Profil İçe Aktarma

LinkedIn profilinin otomatik olarak (API veya kazıma yoluyla) içe
aktarılması bilinçli olarak **eklenmedi**: LinkedIn'in Kullanım
Şartları, oturum/kimlik bilgisi gerektiren otomatik veri çekmeyi (scraping)
yasaklıyor ve resmi API'si bu tür kişisel profil verisine üçüncü taraf
uygulamalar için açık değil. Bu riski almak yerine, bölüm 6'daki "Var
Olan Bir CV'yi Yükle ve Yeniden Yaz" akışı pratik bir alternatif sunar:
LinkedIn profilinin PDF olarak dışa aktarılan hali (LinkedIn > Profili
Düzenle > Daha Fazla > Profili PDF Olarak Kaydet) veya profil metninin
kopyala-yapıştır hâli doğrudan yüklenip aynı ATS-dostu yeniden yazma
işleminden geçirilebilir.

## Testleri Çalıştırma

Tüm birim testleri (Türkçe eşleşme, CV/Ön yazı PDF üretimi, SQLite işlemleri ve Pydantic validasyonları) tek komutla çalıştırılabilir:

```bash
python -m unittest discover -s tests
```

## Gizlilik


`data/profile.json` ve `data/jobs.db` `.gitignore`'da tanımlıdır ve
repoya commit edilmez — kişisel bilgilerin (iletişim bilgileri, taranan
ilanlar) yalnızca kendi makinende kalır.
