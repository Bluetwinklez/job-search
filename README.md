# İş Arama Asistanı

Merkezi bir profilden ATS-dostu (başvuru takip sistemi tarafından kolayca
okunabilen) PDF CV üreten; LinkedIn, Indeed, Glassdoor, Google,
ZipRecruiter, Bayt ve Naukri'den aynı anda iş ilanı tarayıp eşleştirme
skoruyla kaydeden; başvuru durumunu takip eden ve ilana özel ön yazı
taslağı üreten bir araç seti. Hepsi tek bir web arayüzünden kullanılabilir.

## Yol Haritası

- [x] Merkezi profil şeması (`app/models.py`)
- [x] Profilden ATS-dostu PDF CV üretimi (`app/cv_generator.py`)
- [x] Çoklu platformdan iş ilanı tarama + yerel kayıt (`app/job_search.py`, [JobSpy](https://github.com/speedyapply/JobSpy) tabanlı)
- [x] İlan / profil yetenek eşleşme skoru
- [x] Başvuru takibi (durum: yeni/başvuruldu/mülakat/reddedildi/teklif) (`app/tracker.py`)
- [x] İlana özel ön yazı taslağı (`app/cover_letter.py`)
- [x] Web arayüzü (`streamlit_app.py`)
- [ ] İlana özel CV uyarlama (LLM ile)

## Kurulum

```bash
pip install -r requirements.txt
```

## Web Arayüzü (önerilen)

Profil düzenleme, CV oluşturma, iş arama, başvuru takibi ve ön yazı
oluşturmayı tek yerden yapan arayüz:

```bash
streamlit run streamlit_app.py
```

Tarayıcıda `http://localhost:8501` açılır. Sekmeler: **Profil**, **CV
Oluştur**, **İş Ara**, **Başvurularım**, **Ön Yazı**. Aşağıdaki bölümler
aynı işlevlerin komut satırı karşılıklarını anlatır.

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
taranır; `--sites linkedin,indeed` gibi bir alt küme de verilebilir. Bir
platform o ülke/sorgu için desteklenmiyorsa (ör. Glassdoor bazı ülkelerde
çalışmaz) o platform atlanır, uyarı basılır ve diğer platformlardan gelen
sonuçlar yine de kaydedilir.

Sonuçlar `data/jobs.db` (SQLite) içine tekilleştirilerek kaydedilir;
`--profile` verilirse her ilan için profildeki yetenek/teknoloji
anahtar kelimeleriyle basit bir eşleşme skoru (0-1) hesaplanır.

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

LLM gerektirmez: profildeki özet, en güncel deneyim ve (verilirse) ilan
açıklamasıyla eşleşen yetenekleri birleştirip düzenlenebilir bir taslak
üretir.

```bash
python -m app.cover_letter \
  --profile data/profile.json \
  --title "Backend Developer" \
  --company "Acme Tech" \
  --job-description-file ilan.txt \
  --output cover_letter.txt
```
