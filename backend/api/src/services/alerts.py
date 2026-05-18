"""Threshold-based alerting on stock positions."""

from typing import Literal, TypedDict

from loguru import logger

from src.models.pydantic.schema import Alert, FundSchema, StockSchema
from src.services.email_notifier import get_alert_notifier
from src.services.fund import FundService


class AlertCheckResult(TypedDict):
    fund_name: str
    alerts_count: int
    email_sent: bool


def check_stock_alerts(stock: StockSchema) -> list[Alert]:
    """Return all threshold breaches for a single stock."""
    alerts: list[Alert] = []

    if stock.target_repartition is not None:
        diff = stock.current_repartition - stock.target_repartition
        if abs(diff) > stock.arbitration_threshold:
            direction: Literal["over", "under"] = "over" if diff > 0 else "under"
            label = "over-weight" if direction == "over" else "under-weight"
            alerts.append(
                Alert(
                    stock_symbol=stock.symbol,
                    stock_name=stock.name,
                    kind="arbitration",
                    direction=direction,
                    value=round(diff, 2),
                    threshold=stock.arbitration_threshold,
                    message=(
                        f"{stock.symbol} is {label}: "
                        f"current {stock.current_repartition}% vs target "
                        f"{stock.target_repartition}% (Δ {diff:+.2f}%, "
                        f"threshold ±{stock.arbitration_threshold}%)"
                    ),
                )
            )

    glp = stock.gain_loss_percentage
    if glp is not None and abs(glp) > stock.threshold_to_alert:
        gl_direction: Literal["gain", "loss"] = "gain" if glp > 0 else "loss"
        alerts.append(
            Alert(
                stock_symbol=stock.symbol,
                stock_name=stock.name,
                kind="gain_loss",
                direction=gl_direction,
                value=round(glp, 2),
                threshold=stock.threshold_to_alert,
                message=(
                    f"{stock.symbol} significant {gl_direction}: "
                    f"{glp:+.2f}% (threshold ±{stock.threshold_to_alert}%)"
                ),
            )
        )

    return alerts


def check_fund_alerts(fund: FundSchema) -> list[Alert]:
    """Aggregate alerts across all stocks in a fund."""
    alerts: list[Alert] = []
    for stock in fund.stocks:
        alerts.extend(check_stock_alerts(stock))
    return alerts


def check_all_funds_alerts() -> dict[str, tuple[FundSchema, list[Alert]]]:
    """Walk all funds, returning only those with at least one alert."""
    result: dict[str, tuple[FundSchema, list[Alert]]] = {}
    for fund in FundService.get_all():
        alerts = check_fund_alerts(fund)
        if alerts and fund.id is not None:
            result[fund.id] = (fund, alerts)
    return result


def run_alert_check() -> dict[str, AlertCheckResult]:
    """Scheduler entry point: check every fund and send digest emails.

    Wraps everything in try/except so APScheduler never sees an unhandled
    exception that could kill the job.
    """
    summary: dict[str, AlertCheckResult] = {}
    try:
        funds_with_alerts = check_all_funds_alerts()
        logger.info(f"Alert check: {len(funds_with_alerts)} fund(s) with alerts")
        for fund_id, (fund, alerts) in funds_with_alerts.items():
            email_sent = False
            try:
                email_sent = get_alert_notifier().notify_fund_alerts(fund, alerts)
            except Exception as e:
                logger.error(f"Failed sending alert email for fund {fund_id}: {e}")
            summary[fund_id] = {
                "fund_name": fund.fund_name,
                "alerts_count": len(alerts),
                "email_sent": email_sent,
            }
    except Exception as e:
        logger.exception(f"Alert check failed: {e}")
    return summary
