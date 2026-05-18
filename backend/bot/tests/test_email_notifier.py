"""
Tests for EmailNotifier - email sending and notification methods.
Tests all notification types with mocked SMTP.
"""

import pytest

from dca.email_notifier import EmailNotifier


class TestSendEmail:
    """Tests for send_email core method."""

    @pytest.fixture
    def notifier(self, monkeypatch):
        """Create an EmailNotifier with test credentials."""
        monkeypatch.setenv("SMTP_USER", "test@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "password")
        monkeypatch.setenv("EMAIL_TO", "recipient@example.com")
        return EmailNotifier()

    def test_should_return_true_on_success(self, mocker, notifier):
        """
        Should return True when email is sent successfully.

        Given: Valid SMTP credentials and recipient
        When: Sending an email
        Then: Returns True, SMTP methods called correctly
        """
        # Given
        mock_smtp = mocker.patch("shared.email_notifier.smtplib.SMTP")
        mock_server = mock_smtp.return_value.__enter__.return_value

        # When
        result = notifier.send_email("Test Subject", "Test Body")

        # Then
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()

    def test_should_return_false_on_smtp_error(self, mocker, notifier):
        """
        Should return False when SMTP connection fails.

        Given: SMTP server unreachable
        When: Sending an email
        Then: Returns False without raising
        """
        # Given
        mocker.patch(
            "shared.email_notifier.smtplib.SMTP",
            side_effect=Exception("Connection refused"),
        )

        # When
        result = notifier.send_email("Test", "Body")

        # Then
        assert result is False


class TestNotificationMethods:
    """Tests for notification convenience methods."""

    @pytest.fixture
    def notifier(self, monkeypatch):
        """Create an EmailNotifier with test credentials."""
        monkeypatch.setenv("SMTP_USER", "test@example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "password")
        monkeypatch.setenv("EMAIL_TO", "recipient@example.com")
        return EmailNotifier()

    def test_notify_purchase_success_should_include_details(self, mocker, notifier):
        """
        Should send email with purchase details in subject and body.

        Given: Purchase details (symbol, quantity, price, cost, reason)
        When: Calling notify_purchase_success
        Then: Email sent with details in body
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_purchase_success("ETHUSDC", 0.01, 3000.0, 30.0, "momentum buy")

        # Then
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "ETHUSDC" in subject
        assert "3000.0" in body
        assert "30.0" in body

    def test_notify_purchase_skipped_should_include_reason(self, mocker, notifier):
        """
        Should send email with skip reason.

        Given: Symbol and skip reason
        When: Calling notify_purchase_skipped
        Then: Email sent with reason in body
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_purchase_skipped("ETHUSDC", "bullish momentum")

        # Then
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "ETHUSDC" in subject
        assert "bullish momentum" in body

    def test_notify_error_should_include_error_details(self, mocker, notifier):
        """
        Should send email with error type and details.

        Given: Error type and details
        When: Calling notify_error
        Then: Email sent with error info
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_error("API Error", "Connection timeout")

        # Then
        mock_send.assert_called_once()
        subject, body = mock_send.call_args[0]
        assert "Error" in subject
        assert "Connection timeout" in body

    def test_notify_startup_with_next_run(self, mocker, notifier):
        """
        Should include next run time when provided.

        Given: Next run time string
        When: Calling notify_startup with next_run
        Then: Email body includes the schedule time
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_startup(next_run="2026-02-15 10:00:00")

        # Then
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        assert "2026-02-15" in body

    def test_notify_startup_without_next_run(self, mocker, notifier):
        """
        Should send startup email without schedule info when no next_run.

        Given: No next_run parameter
        When: Calling notify_startup
        Then: Email sent successfully
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_startup()

        # Then
        mock_send.assert_called_once()

    def test_notify_crash_should_include_error_message(self, mocker, notifier):
        """
        Should include the crash error message in the email body.

        Given: Error message string
        When: Calling notify_crash
        Then: Email body contains the error message
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_crash("OutOfMemory: heap space")

        # Then
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        assert "OutOfMemory: heap space" in body

    def test_notify_misfire_with_retry(self, mocker, notifier):
        """
        Should mention retry attempt when will_retry is True.

        Given: Missed execution time and will_retry=True
        When: Calling notify_misfire
        Then: Email body mentions retry attempt
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_misfire("2026-02-15 10:00:00", will_retry=True)

        # Then
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        assert "attempt" in body.lower()

    def test_notify_misfire_expired(self, mocker, notifier):
        """
        Should mention expiration when will_retry is False.

        Given: Missed execution time and will_retry=False
        When: Calling notify_misfire
        Then: Email body mentions expiration
        """
        # Given
        mock_send = mocker.patch.object(notifier, "send_email")

        # When
        notifier.notify_misfire("2026-02-15 10:00:00", will_retry=False)

        # Then
        mock_send.assert_called_once()
        body = mock_send.call_args[0][1]
        assert "expired" in body.lower()


class TestEmailNotifierInit:
    """Tests for EmailNotifier initialization."""

    def test_should_not_raise_when_credentials_missing(self, monkeypatch):
        """
        Should initialize without raising when SMTP credentials are missing.

        Given: No SMTP credentials in environment
        When: Creating EmailNotifier
        Then: Instance created with empty credentials
        """
        # Given
        monkeypatch.setenv("SMTP_USER", "")
        monkeypatch.setenv("SMTP_PASSWORD", "")
        monkeypatch.delenv("EMAIL_TO", raising=False)

        # When
        notifier = EmailNotifier()

        # Then
        assert notifier.smtp_user == ""
        assert notifier.to_email is None
