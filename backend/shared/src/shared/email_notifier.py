"""Generic SMTP email notifier shared across services."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from loguru import logger


class EmailNotifier:
    """Simple SMTP email notifier with a configurable subject prefix."""

    def __init__(self, subject_prefix: str = ""):
        self.subject_prefix = subject_prefix
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.free.fr")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = self.smtp_user
        self.to_email = os.getenv("EMAIL_TO")

        if not (self.smtp_user and self.smtp_password):
            logger.warning("SMTP credentials missing")
        if not self.to_email:
            logger.warning("Recipient email (EMAIL_TO) not set")

    def send_email(self, subject: str, body: str) -> bool:
        """Send a plain-text email. Returns True on success."""
        try:
            if not self.to_email:
                raise ValueError("Recipient email (EMAIL_TO) not set")

            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = self.to_email
            full_subject = (
                f"{self.subject_prefix} {subject}".strip()
                if self.subject_prefix
                else subject
            )
            msg["Subject"] = full_subject
            msg["Date"] = formatdate(localtime=True)
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"📧 Email sent: {full_subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
