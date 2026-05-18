"""Unit tests for the alert detection service."""

from src.models.pydantic.schema import FundSchema, StockSchema
from src.services.alerts import (
    check_fund_alerts,
    check_stock_alerts,
    run_alert_check,
)


def _make_stock(
    *,
    current_repartition: float = 50.0,
    target_repartition: float | None = 50.0,
    arbitration_threshold: float = 5.0,
    gain_loss_percentage: float | None = 0.0,
    threshold_to_alert: float = 10.0,
) -> StockSchema:
    return StockSchema(
        id="1",
        name="ACME",
        symbol="ACME",
        shares_number=1.0,
        cost=100.0,
        gain_loss_percentage=gain_loss_percentage,
        current_repartition=current_repartition,
        target_repartition=target_repartition,
        arbitration_threshold=arbitration_threshold,
        threshold_to_alert=threshold_to_alert,
    )


class TestCheckStockAlerts:
    """Threshold rules for a single stock."""

    def test_should_return_empty_when_no_breaches(self):
        """
        Given values comfortably below both thresholds
        When checking
        Then no alerts are emitted
        """
        # Given
        stock = _make_stock(
            current_repartition=51.0,
            target_repartition=50.0,
            gain_loss_percentage=2.0,
        )

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert alerts == []

    def test_should_emit_over_when_arbitration_exceeded_positive(self):
        """
        Given current allocation above target by more than the threshold
        When checking
        Then a single 'arbitration over' alert is emitted
        """
        # Given
        stock = _make_stock(
            current_repartition=60.0,
            target_repartition=50.0,
            arbitration_threshold=5.0,
            gain_loss_percentage=0.0,
        )

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert len(alerts) == 1
        assert alerts[0].kind == "arbitration"
        assert alerts[0].direction == "over"
        assert alerts[0].value == 10.0

    def test_should_emit_under_when_arbitration_exceeded_negative(self):
        """
        Given current allocation below target by more than the threshold
        When checking
        Then a single 'arbitration under' alert is emitted
        """
        # Given
        stock = _make_stock(
            current_repartition=40.0,
            target_repartition=50.0,
            arbitration_threshold=5.0,
        )

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert len(alerts) == 1
        assert alerts[0].direction == "under"
        assert alerts[0].value == -10.0

    def test_should_skip_arbitration_when_target_is_none(self):
        """
        Given no target repartition configured
        When checking
        Then no arbitration alert is emitted even with large gap
        """
        # Given
        stock = _make_stock(target_repartition=None, current_repartition=99.0)

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert alerts == []

    def test_should_not_emit_when_diff_equals_threshold(self):
        """
        Given the gap equals the threshold exactly
        When checking
        Then no alert is emitted (strict > comparison)
        """
        # Given
        stock = _make_stock(
            current_repartition=55.0,
            target_repartition=50.0,
            arbitration_threshold=5.0,
        )

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert alerts == []

    def test_should_emit_gain_when_positive_pct_exceeds_threshold(self):
        """
        Given gain percentage above threshold
        When checking
        Then a 'gain' alert is emitted
        """
        # Given
        stock = _make_stock(gain_loss_percentage=15.0, threshold_to_alert=10.0)

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert len(alerts) == 1
        assert alerts[0].kind == "gain_loss"
        assert alerts[0].direction == "gain"

    def test_should_emit_loss_when_negative_pct_exceeds_threshold(self):
        """
        Given loss percentage exceeding threshold in absolute terms
        When checking
        Then a 'loss' alert is emitted
        """
        # Given
        stock = _make_stock(gain_loss_percentage=-15.0, threshold_to_alert=10.0)

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert len(alerts) == 1
        assert alerts[0].direction == "loss"

    def test_should_skip_gain_loss_when_pct_is_none(self):
        """
        Given gain/loss percentage unavailable
        When checking
        Then no gain_loss alert is emitted
        """
        # Given
        stock = _make_stock(gain_loss_percentage=None)

        # When
        alerts = check_stock_alerts(stock)

        # Then
        assert [a for a in alerts if a.kind == "gain_loss"] == []

    def test_should_emit_both_when_both_rules_breach(self):
        """
        Given both rules breached
        When checking
        Then exactly two alerts are emitted
        """
        # Given
        stock = _make_stock(
            current_repartition=70.0,
            target_repartition=50.0,
            arbitration_threshold=5.0,
            gain_loss_percentage=20.0,
            threshold_to_alert=10.0,
        )

        # When
        alerts = check_stock_alerts(stock)

        # Then
        kinds = sorted(a.kind for a in alerts)
        assert kinds == ["arbitration", "gain_loss"]


class TestCheckFundAlerts:
    def test_should_aggregate_alerts_across_stocks(self):
        """
        Given a fund with one breaching and one healthy stock
        When checking the fund
        Then only the breaching stock's alert is returned
        """
        # Given
        fund = FundSchema(
            id="f1",
            fund_name="F",
            stocks=[
                _make_stock(symbol_override="A", gain_loss_percentage=0.0)
                if False
                else _make_stock(gain_loss_percentage=0.0),
                _make_stock(gain_loss_percentage=50.0, threshold_to_alert=10.0),
            ],
        )

        # When
        alerts = check_fund_alerts(fund)

        # Then
        assert len(alerts) == 1
        assert alerts[0].kind == "gain_loss"


class TestRunAlertCheck:
    def test_should_send_one_email_per_fund_with_alerts(self, mocker):
        """
        Given two funds, one with alerts and one without
        When the scheduler runs the check
        Then the notifier is called exactly once with the breaching fund
        """
        # Given
        healthy = FundSchema(id="h", fund_name="Healthy", stocks=[_make_stock()])
        breaching_stock = _make_stock(
            gain_loss_percentage=50.0, threshold_to_alert=10.0
        )
        breaching = FundSchema(id="b", fund_name="Bad", stocks=[breaching_stock])
        mocker.patch(
            "src.services.alerts.FundService.get_all",
            return_value=[healthy, breaching],
        )
        notifier = mocker.Mock()
        notifier.notify_fund_alerts.return_value = True
        mocker.patch("src.services.alerts.get_alert_notifier", return_value=notifier)

        # When
        summary = run_alert_check()

        # Then
        notifier.notify_fund_alerts.assert_called_once()
        called_fund, called_alerts = notifier.notify_fund_alerts.call_args[0]
        assert called_fund.id == "b"
        assert len(called_alerts) == 1
        assert summary == {
            "b": {"fund_name": "Bad", "alerts_count": 1, "email_sent": True}
        }

    def test_should_swallow_notifier_exceptions(self, mocker):
        """
        Given the email notifier raises
        When the scheduler runs
        Then the run completes with email_sent=False and no exception escapes
        """
        # Given
        breaching = FundSchema(
            id="b",
            fund_name="Bad",
            stocks=[_make_stock(gain_loss_percentage=50.0, threshold_to_alert=10.0)],
        )
        mocker.patch(
            "src.services.alerts.FundService.get_all", return_value=[breaching]
        )
        notifier = mocker.Mock()
        notifier.notify_fund_alerts.side_effect = RuntimeError("SMTP down")
        mocker.patch("src.services.alerts.get_alert_notifier", return_value=notifier)

        # When
        summary = run_alert_check()

        # Then
        assert summary["b"]["email_sent"] is False
