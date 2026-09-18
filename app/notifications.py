"""Bildirim & hatırlatma altyapısı.

Bu modül, uygulama içindeki takip/mülakat hatırlatıcılarından bir günlük
özet (digest) metni üretir ve bunu isteğe bağlı olarak Telegram veya
e-posta (SMTP) üzerinden gönderir.

Önemli: Bu uygulama sürekli çalışan bir sunucu değildir (Streamlit yerel
olarak çalışır). Bu yüzden bildirimler OTOMATİK/arka planda gönderilmez;
kullanıcı web arayüzünden manuel tetikler ya da bu dosyayı kendi işletim
sisteminin zamanlayıcısına (cron, Görev Zamanlayıcı vb.) bağlayarak
otomatikleştirebilir:

    # Örnek cron girdisi (her sabah 09:00'da günlük özeti Telegram'a gönderir)
    0 9 * * * cd /path/to/proje && python -m app.notifications \\
        --db data/jobs.db --telegram-token "$TELEGRAM_BOT_TOKEN" \\
        --telegram-chat-id "$TELEGRAM_CHAT_ID"

Telegram bot token'ı ve chat id'si, e-posta gönderimi için SMTP sunucu
bilgileri ve kimlik bilgileri KULLANICIYA AİTTİR — bu proje sahte veya
varsayılan kimlik bilgisi üretmez/saklamaz.
"""

from __future__ import annotations

import argparse
import smtplib
import urllib.error
import urllib.request
import json
from email.mime.text import MIMEText
from pathlib import Path

from app.job_search import list_upcoming_interviews, list_watched_companies
from app.outreach import check_follow_up_needed


def build_daily_digest(db_path: Path, follow_up_days: int = 7, interview_within_days: int = 3) -> str:
    """Takip zamanı gelmiş başvurular ve yaklaşan mülakatlardan özet metin üretir."""
    lines = ["📋 İş Arama Asistanı — Günlük Özet", ""]

    pending_fu = check_follow_up_needed(db_path, days_threshold=follow_up_days)
    if pending_fu:
        lines.append(f"⏳ Takip zamanı gelmiş {len(pending_fu)} başvuru:")
        for job in pending_fu[:10]:
            lines.append(f"  - {job['title']} @ {job['company']}")
    else:
        lines.append("⏳ Takip zamanı gelmiş başvuru yok.")

    lines.append("")

    upcoming = list_upcoming_interviews(db_path, within_days=interview_within_days)
    if upcoming:
        lines.append(f"🗓️ Önümüzdeki {interview_within_days} gün içinde {len(upcoming)} mülakat:")
        for job in upcoming:
            lines.append(f"  - {job['title']} @ {job['company']} — {job['interview_at']}")
    else:
        lines.append(f"🗓️ Önümüzdeki {interview_within_days} gün içinde planlı mülakat yok.")

    watched = list_watched_companies(db_path)
    if watched:
        lines.append("")
        lines.append(f"🏢 Takip listesindeki {len(watched)} şirket için 'Şirket Takip Listesi' bölümünden yeni ilan kontrolü yapmayı unutma.")

    return "\n".join(lines)


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> None:
    """Telegram Bot API üzerinden mesaj gönderir. bot_token/chat_id kullanıcının kendi Telegram botuna aittir."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Telegram API Hatası ({e.code}): {err_body}")


def send_email_notification(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    to_addr: str,
    subject: str,
    body: str,
    use_tls: bool = True,
) -> None:
    """SMTP üzerinden e-posta bildirimi gönderir. Sunucu bilgileri/kimlik bilgileri kullanıcıya aittir."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_addr

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.sendmail(username, [to_addr], msg.as_string())


def main() -> None:
    parser = argparse.ArgumentParser(description="Günlük özet bildirimini üretir ve isteğe bağlı olarak gönderir.")
    parser.add_argument("--db", type=Path, default=Path("data/jobs.db"))
    parser.add_argument("--follow-up-days", type=int, default=7)
    parser.add_argument("--interview-within-days", type=int, default=3)
    parser.add_argument("--telegram-token", default=None, help="Kendi Telegram bot token'ınız")
    parser.add_argument("--telegram-chat-id", default=None, help="Kendi Telegram chat id'niz")
    parser.add_argument("--smtp-host", default=None)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--smtp-user", default=None)
    parser.add_argument("--smtp-password", default=None)
    parser.add_argument("--email-to", default=None)
    args = parser.parse_args()

    digest = build_daily_digest(args.db, follow_up_days=args.follow_up_days, interview_within_days=args.interview_within_days)
    print(digest)

    if args.telegram_token and args.telegram_chat_id:
        send_telegram_message(args.telegram_token, args.telegram_chat_id, digest)
        print("\nTelegram bildirimi gönderildi.")

    if args.smtp_host and args.smtp_user and args.smtp_password and args.email_to:
        send_email_notification(
            args.smtp_host, args.smtp_port, args.smtp_user, args.smtp_password, args.email_to,
            subject="İş Arama Asistanı — Günlük Özet", body=digest,
        )
        print("\nE-posta bildirimi gönderildi.")


if __name__ == "__main__":
    main()
