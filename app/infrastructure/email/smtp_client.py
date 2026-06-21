import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


async def send_email(
    to: str,
    subject: str,
    html_body: str,
) -> None:
    message = MIMEMultipart("alternative")
    message["From"] = settings.emails_from
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        start_tls=False,
        validate_certs=False,
    )