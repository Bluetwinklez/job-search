# İş Arama Asistanı

Merkezi bir profilden ATS-dostu (başvuru takip sistemi tarafından kolayca
okunabilen) PDF CV üreten ve LinkedIn, Indeed, Glassdoor, Google,
ZipRecruiter, Bayt ve Naukri'den aynı anda iş ilanı tarayıp eşleştirme
skoruyla kaydeden bir araç seti.

## Yol Haritası

- [x] Merkezi profil şeması (`app/models.py`)
- [x] Profilden ATS-dostu PDF CV üretimi (`app/cv_generator.py`)
- [x] Çoklu platformdan iş ilanı tarama + yerel kayıt (`app/job_search.py`, [JobSpy](https://github.com/speedyapply/JobSpy) tabanlı)
- [x] İlan / profil yetenek eşleşme skoru
- [ ] İlana özel CV uyarlama (LLM ile)
- [ ] Başvuru takibi (durum: başvuruldu/mülakat/red)

## Kurulum

```bash
pip install -r requirements.txt
```

## 1. CV Oluşturma

Amaç: standart, tek sütunlu, tablosuz/ikonsuz bir CV — bu format hem ATS
yazılımları tarafından hatasız ayrıştırılır hem de işe alım uzmanlarının
hızlıca tarayabileceği sade bir okunabilirlik sağlar.

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
taranır; `--sites linkedin,indeed` gibi bir alt küme de verilebilir.
Sonuçlar `data/jobs.db` (SQLite) içine tekilleştirilerek kaydedilir;
`--profile` verilirse her ilan için profildeki yetenek/teknoloji
anahtar kelimeleriyle basit bir eşleşme skoru (0-1) hesaplanır.

Diğer parametreler:

- `--hours-old 24` — yalnızca son 24 saatte açılan ilanlar
- `--country-indeed turkey` — Indeed'in ülke bazlı sonuçları için (varsayılan `turkey`)
- `--linkedin-descriptions` — LinkedIn ilanları için de açıklama metnini çek (eşleşme skoru hesaplanabilsin diye; her ilan için ekstra istek attığı için daha yavaştır)
- `--db data/jobs.db` — kayıtların tutulacağı SQLite dosyası

Kayıtlı ilanları eşleşme skoruna göre sıralı listelemek için:

```bash
python -c "
from pathlib import Path
from app.job_search import list_jobs
for row in list_jobs(Path('data/jobs.db'), limit=20, min_score=0.3):
    print(dict(row))
"
```

**Not:** Tarama, ilgili sitelerin herkese açık iş ilanı sonuçlarını
kullanır ([JobSpy](https://github.com/speedyapply/JobSpy) kütüphanesi
üzerinden). Sık/yüksek hacimli istek atmak ilgili sitenin kullanım
koşullarını ihlal edebilir ve IP engellemesine yol açabilir; `--results`
değerini makul tut ve gereğinden sık çalıştırma.
