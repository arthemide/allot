"""Email notification helper for DCA bot key events."""

from typing import Optional

from shared.email_notifier import EmailNotifier as SharedEmailNotifier


class EmailNotifier(SharedEmailNotifier):
    """DCA-flavored email notifier with bot-specific helper methods."""

    def __init__(self):
        super().__init__(subject_prefix="[DCA Bot]")

    def notify_purchase_success(
        self, symbol: str, quantity: float, price: float, cost: float, reason: str
    ):
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
        subject = f"⏭️ Purchase Skipped - {symbol}"
        body = f"""DCA Purchase Skipped

Symbol: {symbol}
Reason: {reason}

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)

    def notify_error(self, error_type: str, details: str):
        subject = f"❌ Error - {error_type}"
        body = f"""DCA Bot Error

Error Type: {error_type}
Details: {details}

Please check the logs for more information.

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)

    def notify_startup(self, next_run: Optional[str] = None):
        subject = "🚀 Bot Started"
        body = """DCA Bot Started Successfully

The DCA bot is now running.
"""
        if next_run:
            body += f"Next scheduled execution: {next_run}\n"
        body += "\nThis is an automated notification from your DCA bot."
        self.send_email(subject, body)

    def notify_crash(self, error_message: str):
        subject = "💥 Bot Crashed"
        body = f"""DCA Bot Crashed

The DCA bot encountered a critical error and stopped running.

Error: {error_message}

The bot will automatically restart if managed by launchd/systemd.
Please check the logs for more details.

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)

    def notify_reconciliation_drift(
        self, asset: str, local_qty: str, broker_qty: str, drift: str
    ):
        subject = f"⚠️ Position Drift Detected - {asset}"
        body = f"""Position Reconciliation Alert

The locally tracked position no longer matches the Binance spot balance.

Asset: {asset}
Local quantity: {local_qty}
Binance balance (free + locked): {broker_qty}
Drift (broker - local): {drift}

Possible causes: sell/withdrawal/conversion made outside the bot,
funds moved to Earn/staking, or an incorrect historical seed
(DCA_BASE_QUANTITY / DCA_BASE_PRUM).

Please review and adjust the local records.

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)

    def notify_misfire(self, missed_time: str, will_retry: bool = True):
        subject = "⏰ Missed Execution Detected"
        retry_info = (
            "The bot will attempt to execute the purchase now."
            if will_retry
            else "The execution window has expired."
        )
        body = f"""DCA Scheduled Execution Missed

The scheduled execution at {missed_time} was missed because the bot was not running.

{retry_info}

This is an automated notification from your DCA bot.
"""
        self.send_email(subject, body)


_notifier: Optional[EmailNotifier] = None


def get_notifier() -> EmailNotifier:
    """Get or create the global email notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = EmailNotifier()
    return _notifier
