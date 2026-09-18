"""İş arama sürecinde İK ve yöneticilere gönderilecek LinkedIn bağlantı, soğuk mesaj ve takip e-postası üreticisi."""

from __future__ import annotations

from app.models import Profile


def generate_linkedin_connection_note(
    profile: Profile,
    job_title: str,
    company: str,
    recipient_name: str | None = None,
) -> str:
    """LinkedIn 300 karakter sınırına uygun profesyonel bağlantı isteği notu üretir."""
    salutation = f"Merhaba {recipient_name}," if recipient_name else "Merhaba,"
    note = (
        f"{salutation} {company} bünyesindeki {job_title} ilanınızı ilgiyle inceledim. "
        f"{profile.contact.title} olarak deneyimimin ekibinize değer katacağına inanıyorum. "
        f"Ağımda yer almanızdan onur duyarım. Saygılarımla, {profile.contact.full_name}"
    )
    # 300 karakter sınırını garanti et
    if len(note) > 300:
        note = (
            f"{salutation} {company} {job_title} pozisyonuna başvurdum. "
            f"{profile.contact.title} tecrübemle ekibinize katkı sunmak isterim. "
            f"Ağımda olmanızdan memnuniyet duyarım. {profile.contact.full_name}"
        )
    return note[:300]


def generate_cold_email(
    profile: Profile,
    job_title: str,
    company: str,
    recipient_name: str | None = None,
) -> tuple[str, str]:
    """İşe alım yöneticisine gönderilecek profesyonel soğuk e-posta (Konu, İçerik) döner."""
    subject = f"{job_title} Başvurusu — {profile.contact.full_name}"
    salutation = f"Sayın {recipient_name}," if recipient_name else "Sayın Yetkili,"
    latest_exp = profile.experience[0] if profile.experience else None
    latest_info = (
        f"{latest_exp.company} bünyesindeki {latest_exp.role} rolümde "
        f"{', '.join(latest_exp.tech_stack[:3]) if latest_exp.tech_stack else 'alanımda'} çalışmalar gerçekleştirdim."
        if latest_exp
        else ""
    )

    body = f"""{salutation}

{company} bünyesinde açık bulunan {job_title} pozisyonuna başvurumu ilettim. {profile.summary or ''}

{latest_info}

Deneyimlerimin ve işe olan motivasyonumun {company} ekibine hızla katkı sağlayacağına inanıyorum. CV'm ve portföyüm ekte/profilimde mevcuttur.

Pozisyona uygunluğumu kısaca değerlendirmek üzere sizinle 10-15 dakikalık bir ön görüşme gerçekleştirmekten büyük mutluluk duyarım.

İlginiz ve vaktiniz için teşekkür ederim.

Saygılarımla,
{profile.contact.full_name}
{profile.contact.title}
{profile.contact.email} | {profile.contact.phone or ''}
"""
    return subject, body.strip()


def generate_follow_up_email(
    profile: Profile,
    job_title: str,
    company: str,
    days_ago: int = 7,
) -> tuple[str, str]:
    """Başvurudan belirli bir süre sonra yanıt alınamadığında gönderilecek nazik durum takip e-postası."""
    subject = f"Takip: {job_title} Başvurusu Durumu — {profile.contact.full_name}"
    body = f"""Sayın Yetkili,

Yaklaşık {days_ago} gün önce {company} bünyesindeki {job_title} pozisyonuna yaptığım başvuruya istinaden yazıyorum.

Şirketinizin hedeflerine katkı sunma konusundaki heyecanım devam ediyor. Başvuru sürecimin güncel durumu hakkında bilgi alma imkanım var mıdır?

Gerekirse ek bilgi, referans veya vaka çalışması paylaşmaktan memnuniyet duyarım.

Değerli vaktiniz için şimdiden teşekkür eder, iyi çalışmalar dilerim.

Saygılarımla,
{profile.contact.full_name}
{profile.contact.email}
"""
    return subject, body.strip()


def generate_thank_you_email(
    profile: Profile,
    job_title: str,
    company: str,
    interviewer_name: str | None = None,
) -> tuple[str, str]:
    """Mülakat sonrasında 24 saat içinde gönderilecek teşekkür e-postası."""
    subject = f"Teşekkürler: {job_title} Mülakatı — {profile.contact.full_name}"
    salutation = f"Sayın {interviewer_name}," if interviewer_name else "Sayın Yetkili,"
    body = f"""{salutation}

Bugün {company} bünyesindeki {job_title} pozisyonu için gerçekleştirdiğimiz verimli görüşme için içtenlikle teşekkür ederim.

Ekibinizin projelerini ve vizyonunu dinlemek pozisyona olan ilgimi ve motivasyonumu daha da artırdı. Sahip olduğum deneyim ve yetkinliklerle ekibinize katma değer sağlayabileceğime olan inancım tam.

Süreçteki bir sonraki aşamayı sabırsızlıkla bekliyorum. Tekrar görüşmek dileğiyle.

Saygılarımla,
{profile.contact.full_name}
{profile.contact.email}
"""
    return subject, body.strip()
