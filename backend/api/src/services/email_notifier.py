"""Alert email notifier for the Stock Alerting API."""

from typing import Optional

from shared.email_notifier import EmailNotifier
from src.models.pydantic.schema import Alert, FundSchema


class AlertEmailNotifier(EmailNotifier):
    """Stock-alerting-flavored email notifier."""

    def __init__(self):
        super().__init__(subject_prefix="[Stock Alerting]")

    def notify_fund_alerts(self, fund: FundSchema, alerts: list[Alert]) -> bool:
        """Send a single digest email for one fund's alerts. No-op if empty."""
        if not alerts:
            return False
        subject = f"{len(alerts)} alert(s) for {fund.fund_name}"
        body = _format_email_body(fund, alerts)
        return self.send_email(subject, body)


def _format_email_body(fund: FundSchema, alerts: list[Alert]) -> str:
    lines = [
        f"Alert summary for fund: {fund.fund_name}",
        f"Total alerts: {len(alerts)}",
        "",
    ]
    arb = [a for a in alerts if a.kind == "arbitration"]
    gl = [a for a in alerts if a.kind == "gain_loss"]
    if arb:
        lines.append("== Arbitration breaches ==")
        for a in arb:
            lines.append(f"  - {a.message}")
        lines.append("")
    if gl:
        lines.append("== Gain/Loss breaches ==")
        for a in gl:
            lines.append(f"  - {a.message}")
        lines.append("")
    lines.append("This is an automated notification from Stock Alerting.")
    return "\n".join(lines)


_notifier: Optional[AlertEmailNotifier] = None


def get_alert_notifier() -> AlertEmailNotifier:
    global _notifier
    if _notifier is None:
        _notifier = AlertEmailNotifier()
    return _notifier
