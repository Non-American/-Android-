import logging, smtplib
from email.message import EmailMessage
from html import escape

from . import config
from .security import make_token

log = logging.getLogger("orbita.mail")
outbox: list[EmailMessage] = []  # used when SMTP is not configured


def send(to, subject, text, html=None):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.SMTP_FROM, to, subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    if not config.SMTP_HOST:
        log.warning("SMTP не настроен; письмо для %s «%s»:\n%s", to, subject, text)
        outbox.append(msg)
        del outbox[:-100]
        return
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
            if config.SMTP_STARTTLS:
                s.starttls()
            if config.SMTP_USER:
                s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    except (OSError, smtplib.SMTPException):
        log.exception("не удалось отправить письмо %s", to)


def verify_link(uid, email):
    tok = make_token(uid, typ="verify", ttl=48 * 3600, email=email)
    return f"{config.PUBLIC_URL}/api/verify-email?token={tok}"


def send_verification(uid, email, name):
    link = verify_link(uid, email)
    send(email, "Подтвердите email — Orbita",
         f"{name}, здравствуйте!\n\nПодтвердите адрес, чтобы смотреть ленту и переписываться:\n{link}\n\n"
         "Ссылка действует 48 часов. Если вы не регистрировались в Orbita, просто проигнорируйте письмо.",
         f"""<div style="font-family:Helvetica,Arial,sans-serif;max-width:520px;margin:auto;color:#111">
<p style="font-size:28px;font-weight:700;letter-spacing:.04em;margin:24px 0">ORBITA</p>
<p>{escape(name)}, здравствуйте!</p>
<p>Подтвердите адрес, чтобы смотреть ленту и переписываться.</p>
<p><a href="{escape(link)}" style="display:inline-block;background:#111;color:#fff;padding:14px 22px;
text-decoration:none;font-size:12px;letter-spacing:.12em;font-weight:600">ПОДТВЕРДИТЬ EMAIL</a></p>
<p style="color:#666;font-size:13px">Ссылка действует 48 часов. Если вы не регистрировались в Orbita,
просто проигнорируйте письмо.</p></div>""")
