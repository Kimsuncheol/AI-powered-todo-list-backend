from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from app.core.config import settings


conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_sender,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_host,
    MAIL_FROM_NAME="AI Todo",
    MAIL_STARTTLS=settings.mail_use_tls,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


async def send_mail(subject: str, recipients: list[str], body: str) -> None:
    message = MessageSchema(subject=subject, recipients=recipients, body=body, subtype="html")
    mailer = FastMail(conf)
    await mailer.send_message(message)
