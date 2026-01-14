"""
Simple email notification helper for DCA bot key events.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from typing import Optional
from loguru import logger


class EmailNotifier:
    """Simple email notifier using SMTP."""
    
    def __init__(self):
        """Initialize email notifier from environment variables."""
        self.smtp_server = "smtp.free.fr"
        self.smtp_port = 587
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = self.smtp_user
        self.to_email = os.getenv("EMAIL_TO")
        
        if not (self.smtp_user and self.smtp_password):
            logger.warning("SMTP credentials missing")

        if not self.to_email:
            logger.warning("Recipient email (EMAIL_TO) not set")
    
    def send_email(self, subject: str, body: str) -> bool:
        """
        Send email notification.
        
        Args:
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            True if sent successfully, False otherwise
        """        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = f"[DCA Bot] {subject}"
            msg['Date'] = formatdate(localtime=True)
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"📧 Email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def notify_purchase_success(self, symbol: str, quantity: float, price: float, cost: float, reason: str):
        """Notify successful purchase."""
        subject = f"✅ Purchase Executed - {symbol}"
        body = f"""DCA Purchase Successful

Symbol: {symbol}
Quantity: {quantity}
Average Price: {price}
Total Cost: {cost}
Reason: {reason}

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)
    
    def notify_purchase_skipped(self, symbol: str, reason: str):
        """Notify skipped purchase."""
        subject = f"⏭️ Purchase Skipped - {symbol}"
        body = f"""DCA Purchase Skipped

Symbol: {symbol}
Reason: {reason}

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)
    
    def notify_error(self, error_type: str, details: str):
        """Notify error."""
        subject = f"❌ Error - {error_type}"
        body = f"""DCA Bot Error

Error Type: {error_type}
Details: {details}

Please check the logs for more information.

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)
    
    def notify_startup(self, next_run: Optional[str] = None):
        """Notify bot startup."""
        subject = "🚀 Bot Started"
        body = f"""DCA Bot Started Successfully

The DCA bot is now running.
"""
        if next_run:
            body += f"Next scheduled execution: {next_run}\n"
        
        body += "\nThis is an automated notification from your DCA bot."
        self.send_email(subject, body)


# Global instance
_notifier: Optional[EmailNotifier] = None


def get_notifier() -> EmailNotifier:
    """Get or create the global email notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier
