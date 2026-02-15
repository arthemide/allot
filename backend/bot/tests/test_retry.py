"""
Tests for retry_with_backoff decorator.
Tests exponential backoff, retry logic, and exception filtering.
"""

import pytest

from dca.retry import retry_with_backoff


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_should_return_result_when_no_error(self, mocker):
        """
        Should return function result immediately when no exception occurs.

        Given: A function that succeeds on first call
        When: Calling the decorated function
        Then: Returns result without retries
        """
        # Given
        mocker.patch("dca.retry.time.sleep")

        @retry_with_backoff(max_retries=3)
        def succeeds():
            return "ok"

        # When
        result = succeeds()

        # Then
        assert result == "ok"

    def test_should_retry_and_succeed_on_later_attempt(self, mocker):
        """
        Should retry and return result when function succeeds after failures.

        Given: A function that fails twice then succeeds
        When: Calling the decorated function
        Then: Returns result after 3 attempts, sleeps between retries
        """
        # Given
        mock_sleep = mocker.patch("dca.retry.time.sleep")
        call_count = 0

        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def fails_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "ok"

        # When
        result = fails_then_succeeds()

        # Then
        assert result == "ok"
        assert call_count == 3
        assert mock_sleep.call_count == 2

    def test_should_raise_after_max_retries_exhausted(self, mocker):
        """
        Should raise the last exception after all retries are exhausted.

        Given: A function that always fails
        When: Calling the decorated function with max_retries=2
        Then: Raises ValueError after 3 total attempts
        """
        # Given
        mocker.patch("dca.retry.time.sleep")

        @retry_with_backoff(max_retries=2, exceptions=(ValueError,))
        def always_fails():
            raise ValueError("permanent failure")

        # When / Then
        with pytest.raises(ValueError, match="permanent failure"):
            always_fails()

    def test_should_apply_exponential_backoff_delays(self, mocker):
        """
        Should double delay between each retry attempt.

        Given: backoff_factor=2.0 and initial_delay=1.0
        When: Function fails 3 times
        Then: Sleep delays are 1.0, 2.0, 4.0 seconds
        """
        # Given
        mock_sleep = mocker.patch("dca.retry.time.sleep")

        @retry_with_backoff(
            max_retries=3, initial_delay=1.0, backoff_factor=2.0
        )
        def always_fails():
            raise Exception("fail")

        # When
        with pytest.raises(Exception):
            always_fails()

        # Then
        assert mock_sleep.call_args_list[0][0][0] == 1.0
        assert mock_sleep.call_args_list[1][0][0] == 2.0
        assert mock_sleep.call_args_list[2][0][0] == 4.0

    def test_should_not_catch_unspecified_exceptions(self, mocker):
        """
        Should let exceptions not in the exceptions tuple propagate immediately.

        Given: Decorator configured to catch only ValueError
        When: Function raises TypeError
        Then: TypeError propagates without retry
        """
        # Given
        mock_sleep = mocker.patch("dca.retry.time.sleep")

        @retry_with_backoff(max_retries=3, exceptions=(ValueError,))
        def raises_type_error():
            raise TypeError("wrong type")

        # When / Then
        with pytest.raises(TypeError, match="wrong type"):
            raises_type_error()

        mock_sleep.assert_not_called()

    def test_should_preserve_function_name(self, mocker):
        """
        Should preserve the original function's __name__ attribute.

        Given: A decorated function named "my_func"
        When: Inspecting the decorated function
        Then: __name__ is still "my_func"
        """
        # Given
        @retry_with_backoff()
        def my_func():
            pass

        # Then
        assert my_func.__name__ == "my_func"
