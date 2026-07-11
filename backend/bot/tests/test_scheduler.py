"""
Tests for DCAScheduler - job execution, misfire handling, and schedule setup.
Tests key scheduler methods with mocked dependencies.
"""

from datetime import datetime

import pytest

from dca.scheduler import DCAScheduler


@pytest.fixture
def dca_scheduler(mocker):
    """Create a DCAScheduler with mocked dependencies."""
    mocker.patch("dca.scheduler.create_dca_executor")
    mocker.patch("dca.scheduler.BlockingScheduler")

    config = mocker.Mock()
    config.dca = mocker.Mock(
        symbol="ETHUSDC",
        base_asset="ETH",
        quote_asset="USDC",
        amount_usdc=30.0,
        days_of_month="1,15",
        execution_hour=10,
        execution_minute=2,
        grace_period_days=7,
    )
    config.__str__ = mocker.Mock(return_value="MockConfig")

    return DCAScheduler(config)


class TestDCAJob:
    """Tests for _dca_job method."""

    def test_should_run_executor_when_db_healthy(self, mocker, dca_scheduler):
        """
        Should call dca_executor.run() when database is healthy.

        Given: Database health check passes
        When: Running the DCA job
        Then: dca_executor.run() is called
        """
        # Given
        mocker.patch("dca.scheduler.check_db_health", return_value=(True, "DB healthy"))

        # When
        dca_scheduler._dca_job()

        # Then
        dca_scheduler.dca_executor.run.assert_called_once()

    def test_should_skip_when_db_unhealthy(self, mocker, dca_scheduler):
        """
        Should skip execution and notify when database is unhealthy.

        Given: Database health check fails
        When: Running the DCA job
        Then: dca_executor.run() is NOT called, error notification sent
        """
        # Given
        mocker.patch(
            "dca.scheduler.check_db_health", return_value=(False, "Connection refused")
        )
        mock_notifier = mocker.patch("dca.scheduler.get_notifier")

        # When
        dca_scheduler._dca_job()

        # Then
        dca_scheduler.dca_executor.run.assert_not_called()
        mock_notifier.return_value.notify_error.assert_called_once()

    def test_should_notify_crash_on_exception(self, mocker, dca_scheduler):
        """
        Should send crash notification when job raises unexpected exception.

        Given: check_db_health raises an exception
        When: Running the DCA job
        Then: Crash notification sent
        """
        # Given
        mocker.patch("dca.scheduler.check_db_health", side_effect=RuntimeError("boom"))
        mock_notifier = mocker.patch("dca.scheduler.get_notifier")

        # When
        dca_scheduler._dca_job()

        # Then
        mock_notifier.return_value.notify_crash.assert_called_once()


class TestGetLastPurchaseInfo:
    """Tests for _get_last_purchase_info method."""

    def test_should_return_formatted_info_when_purchase_exists(self, dca_scheduler):
        """
        Should return formatted string with date and days ago.

        Given: Recent purchase exists in tracker
        When: Getting last purchase info
        Then: Returns string containing the purchase date
        """
        # Given
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = [
            {"timestamp": "2026-02-10T10:00:00"}
        ]

        # When
        result = dca_scheduler._get_last_purchase_info()

        # Then
        assert result is not None
        assert "2026-02-10" in result

    def test_should_return_none_when_no_purchases(self, dca_scheduler):
        """
        Should return None when no recent purchases exist.

        Given: Tracker has no purchases
        When: Getting last purchase info
        Then: Returns None
        """
        # Given
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = []

        # When
        result = dca_scheduler._get_last_purchase_info()

        # Then
        assert result is None

    def test_should_return_none_on_error(self, dca_scheduler):
        """
        Should return None when tracker raises an exception.

        Given: Tracker raises an exception
        When: Getting last purchase info
        Then: Returns None
        """
        # Given
        dca_scheduler.dca_executor.tracker.get_recent_purchases.side_effect = Exception(
            "DB error"
        )

        # When
        result = dca_scheduler._get_last_purchase_info()

        # Then
        assert result is None

    def test_should_return_none_when_no_timestamp(self, dca_scheduler):
        """
        Should return None when purchase has no timestamp field.

        Given: Purchase dict without timestamp key
        When: Getting last purchase info
        Then: Returns None
        """
        # Given
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = [
            {"quantity": "0.01"}
        ]

        # When
        result = dca_scheduler._get_last_purchase_info()

        # Then
        assert result is None


class TestWasPurchaseMadeAround:
    """Tests for _was_purchase_made_around method."""

    def test_should_return_true_when_purchase_within_one_day(self, dca_scheduler):
        """
        Should return True when a purchase was made within 24h of scheduled time.

        Given: Purchase at 12:00 on the same day as scheduled 10:00
        When: Checking if purchase was made around scheduled time
        Then: Returns True
        """
        # Given
        scheduled = datetime(2026, 2, 10, 10, 0, 0)
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = [
            {"timestamp": "2026-02-10T12:00:00"}
        ]

        # When
        result = dca_scheduler._was_purchase_made_around(scheduled)

        # Then
        assert result is True

    def test_should_return_false_when_no_purchase_nearby(self, dca_scheduler):
        """
        Should return False when no purchase was made near the scheduled time.

        Given: Purchase 5 days before scheduled time
        When: Checking if purchase was made around scheduled time
        Then: Returns False
        """
        # Given
        scheduled = datetime(2026, 2, 10, 10, 0, 0)
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = [
            {"timestamp": "2026-02-05T10:00:00"}
        ]

        # When
        result = dca_scheduler._was_purchase_made_around(scheduled)

        # Then
        assert result is False

    def test_should_return_false_when_no_purchases(self, dca_scheduler):
        """
        Should return False when no purchases exist at all.

        Given: Empty purchase history
        When: Checking if purchase was made around scheduled time
        Then: Returns False
        """
        # Given
        scheduled = datetime(2026, 2, 10, 10, 0, 0)
        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = []

        # When
        result = dca_scheduler._was_purchase_made_around(scheduled)

        # Then
        assert result is False

    def test_should_return_false_on_error(self, dca_scheduler):
        """
        Should return False when tracker raises an exception.

        Given: Tracker raises an error
        When: Checking if purchase was made around scheduled time
        Then: Returns False
        """
        # Given
        scheduled = datetime(2026, 2, 10, 10, 0, 0)
        dca_scheduler.dca_executor.tracker.get_recent_purchases.side_effect = Exception(
            "DB error"
        )

        # When
        result = dca_scheduler._was_purchase_made_around(scheduled)

        # Then
        assert result is False


class TestCheckAndHandleMisfires:
    """Tests for _check_and_handle_misfires method."""

    def test_should_execute_missed_job_within_grace_period(self, mocker, dca_scheduler):
        """
        Should execute missed DCA job when within grace period.

        Given: Today is Feb 15, day 1 was missed, no purchase made around it
        When: Checking for misfires
        Then: Executes _dca_job and sends misfire notification
        """
        # Given
        mocker.patch(
            "dca.scheduler.datetime",
            wraps=datetime,
        )
        mocker.patch("dca.scheduler.datetime").now.return_value = datetime(
            2026, 2, 5, 12, 0, 0
        )

        mock_notifier = mocker.patch("dca.scheduler.get_notifier")

        dca_scheduler.dca_executor.tracker.get_recent_purchases.return_value = []
        mocker.patch.object(dca_scheduler, "_dca_job")
        mocker.patch.object(dca_scheduler, "_get_last_purchase_info", return_value=None)
        mocker.patch.object(
            dca_scheduler, "_was_purchase_made_around", return_value=False
        )

        # When
        dca_scheduler._check_and_handle_misfires()

        # Then
        dca_scheduler._dca_job.assert_called_once()
        mock_notifier.return_value.notify_misfire.assert_called_once()

    def test_should_skip_when_purchase_already_made(self, mocker, dca_scheduler):
        """
        Should not execute when purchase was already made around scheduled time.

        Given: Today is Feb 5, day 1 was "missed" but purchase exists nearby
        When: Checking for misfires
        Then: _dca_job is NOT called
        """
        # Given
        mocker.patch("dca.scheduler.datetime").now.return_value = datetime(
            2026, 2, 5, 12, 0, 0
        )

        mocker.patch.object(dca_scheduler, "_dca_job")
        mocker.patch.object(
            dca_scheduler, "_get_last_purchase_info", return_value="2026-02-01 10:02"
        )
        mocker.patch.object(
            dca_scheduler, "_was_purchase_made_around", return_value=True
        )

        # When
        dca_scheduler._check_and_handle_misfires()

        # Then
        dca_scheduler._dca_job.assert_not_called()


class TestSetupSchedule:
    """Tests for setup_schedule method."""

    def test_should_configure_cron_trigger(self, dca_scheduler):
        """
        Should add job with CronTrigger matching config.

        Given: Config with days_of_month="1,15", hour=10, minute=2
        When: Setting up schedule
        Then: DCA and reconciliation jobs added to scheduler
        """
        # When
        dca_scheduler.setup_schedule()

        # Then
        job_ids = [
            call.kwargs["id"] for call in dca_scheduler.scheduler.add_job.call_args_list
        ]
        assert job_ids == ["dca_job", "reconciliation_job"]

    def test_should_raise_when_no_days_configured(self, mocker, dca_scheduler):
        """
        Should raise ValueError when days_of_month is empty.

        Given: Config with empty days_of_month
        When: Setting up schedule
        Then: ValueError raised
        """
        # Given
        dca_scheduler.config.dca.days_of_month = ""

        # When / Then
        with pytest.raises(ValueError, match="DCA_DAYS_OF_MONTH"):
            dca_scheduler.setup_schedule()


class TestRunOnce:
    """Tests for run_once method."""

    def test_should_call_dca_job(self, mocker, dca_scheduler):
        """
        Should call _dca_job once for manual execution.

        Given: Scheduler initialized
        When: Calling run_once
        Then: _dca_job is called
        """
        # Given
        mocker.patch.object(dca_scheduler, "_dca_job")

        # When
        dca_scheduler.run_once()

        # Then
        dca_scheduler._dca_job.assert_called_once()


class TestShutdown:
    """Tests for shutdown method."""

    def test_should_shutdown_scheduler(self, dca_scheduler):
        """
        Should call scheduler.shutdown with wait=True.

        Given: Scheduler running
        When: Calling shutdown
        Then: BlockingScheduler.shutdown(wait=True) called
        """
        # When
        dca_scheduler.shutdown()

        # Then
        dca_scheduler.scheduler.shutdown.assert_called_once_with(wait=True)
