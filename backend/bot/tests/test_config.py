"""
Tests for Config - validation, environment loading, and string representation.
"""

import pytest

from dca.config import Config


class TestConfigValidation:
    """Tests for Config initialization and validation."""

    @pytest.fixture(autouse=True)
    def _set_required_env(self, monkeypatch):
        """Set required environment variables for Config initialization."""
        monkeypatch.setenv("BINANCE_API_KEY", "test_key")
        monkeypatch.setenv("BINANCE_API_SECRET", "test_secret")
        monkeypatch.setenv("DCA_AMOUNT_USDC", "30.0")
        monkeypatch.setenv("DCA_BASE_PRUM", "")

    def test_should_load_defaults_when_minimal_env_set(self):
        """
        Should initialize with default values when only required env vars are set.

        Given: BINANCE_API_KEY, BINANCE_API_SECRET, DCA_AMOUNT_USDC set
        When: Creating Config instance
        Then: Default values applied for symbol, schedule, strategy
        """
        # When
        config = Config()

        # Then
        assert config.dca.symbol == "ETHUSDC"
        assert config.dca.amount_usdc == 30.0
        assert config.dca.execution_hour == 10
        assert config.dca.execution_minute == 2
        assert config.dca.prum_buffer == 0.03
        assert config.dca.momentum_periods == 2
        assert config.dca.kline_interval == "1w"
        assert config.binance.api_key == "test_key"
        assert config.binance.api_secret == "test_secret"

    def test_should_raise_when_api_key_missing(self, monkeypatch):
        """
        Should raise ValueError when BINANCE_API_KEY is not set.

        Given: BINANCE_API_KEY not in environment
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.delenv("BINANCE_API_KEY", raising=False)

        # When / Then
        with pytest.raises(ValueError, match="BINANCE_API_KEY"):
            Config()

    def test_should_raise_when_api_secret_missing(self, monkeypatch):
        """
        Should raise ValueError when BINANCE_API_SECRET is not set.

        Given: BINANCE_API_SECRET not in environment
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.delenv("BINANCE_API_SECRET", raising=False)

        # When / Then
        with pytest.raises(ValueError, match="BINANCE_API_SECRET"):
            Config()

    def test_should_raise_when_amount_zero(self, monkeypatch):
        """
        Should raise ValueError when DCA_AMOUNT_USDC is 0.

        Given: DCA_AMOUNT_USDC set to 0
        When: Creating Config instance
        Then: ValueError raised with descriptive message
        """
        # Given
        monkeypatch.setenv("DCA_AMOUNT_USDC", "0")

        # When / Then
        with pytest.raises(ValueError, match="greater than 0"):
            Config()

    def test_should_raise_when_amount_negative(self, monkeypatch):
        """
        Should raise ValueError when DCA_AMOUNT_USDC is negative.

        Given: DCA_AMOUNT_USDC set to -10
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_AMOUNT_USDC", "-10")

        # When / Then
        with pytest.raises(ValueError, match="greater than 0"):
            Config()

    def test_should_raise_when_hour_invalid(self, monkeypatch):
        """
        Should raise ValueError when execution hour is out of range.

        Given: DCA_EXECUTION_HOUR set to 25
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_EXECUTION_HOUR", "25")

        # When / Then
        with pytest.raises(ValueError, match="between 0 and 23"):
            Config()

    def test_should_raise_when_minute_invalid(self, monkeypatch):
        """
        Should raise ValueError when execution minute is out of range.

        Given: DCA_EXECUTION_MINUTE set to 60
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_EXECUTION_MINUTE", "60")

        # When / Then
        with pytest.raises(ValueError, match="between 0 and 59"):
            Config()

    def test_should_raise_when_prum_buffer_too_high(self, monkeypatch):
        """
        Should raise ValueError when prum_buffer exceeds 0.5.

        Given: DCA_PRUM_BUFFER set to 0.6
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_PRUM_BUFFER", "0.6")

        # When / Then
        with pytest.raises(ValueError, match="between 0 and 0.5"):
            Config()

    def test_should_raise_when_momentum_periods_too_high(self, monkeypatch):
        """
        Should raise ValueError when momentum_periods exceeds 10.

        Given: DCA_MOMENTUM_PERIODS set to 11
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_MOMENTUM_PERIODS", "11")

        # When / Then
        with pytest.raises(ValueError, match="between 1 and 10"):
            Config()

    def test_should_raise_when_momentum_periods_zero(self, monkeypatch):
        """
        Should raise ValueError when momentum_periods is 0.

        Given: DCA_MOMENTUM_PERIODS set to 0
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_MOMENTUM_PERIODS", "0")

        # When / Then
        with pytest.raises(ValueError, match="between 1 and 10"):
            Config()

    def test_should_raise_when_kline_interval_invalid(self, monkeypatch):
        """
        Should raise ValueError when kline_interval is not in valid list.

        Given: DCA_KLINE_INTERVAL set to "5m"
        When: Creating Config instance
        Then: ValueError raised
        """
        # Given
        monkeypatch.setenv("DCA_KLINE_INTERVAL", "5m")

        # When / Then
        with pytest.raises(ValueError, match="must be one of"):
            Config()

    def test_should_load_base_prum_from_env(self, monkeypatch):
        """
        Should parse DCA_BASE_PRUM as float when set.

        Given: DCA_BASE_PRUM set to "2500.0"
        When: Creating Config instance
        Then: base_prum is 2500.0
        """
        # Given
        monkeypatch.setenv("DCA_BASE_PRUM", "2500.0")

        # When
        config = Config()

        # Then
        assert config.dca.base_prum == 2500.0

    def test_should_have_none_base_prum_when_not_set(self):
        """
        Should set base_prum to None when DCA_BASE_PRUM is not in environment.

        Given: DCA_BASE_PRUM not set
        When: Creating Config instance
        Then: base_prum is None
        """
        # When
        config = Config()

        # Then
        assert config.dca.base_prum is None


class TestConfigStringRepresentation:
    """Tests for Config __str__ method."""

    @pytest.fixture(autouse=True)
    def _set_required_env(self, monkeypatch):
        """Set required environment variables for Config initialization."""
        monkeypatch.setenv("BINANCE_API_KEY", "test_key")
        monkeypatch.setenv("BINANCE_API_SECRET", "test_secret")
        monkeypatch.setenv("DCA_AMOUNT_USDC", "30.0")
        monkeypatch.setenv("DCA_BASE_PRUM", "")

    def test_str_should_display_symbol_and_amount(self):
        """
        Should include symbol and amount in string representation.

        Given: Valid config
        When: Converting to string
        Then: Contains symbol and amount
        """
        # Given
        config = Config()

        # When
        result = str(config)

        # Then
        assert "ETHUSDC" in result
        assert "30.0" in result

    def test_str_should_not_expose_api_secrets(self):
        """
        Should not include API secrets in string representation.

        Given: Config with API secrets
        When: Converting to string
        Then: Secrets are not visible
        """
        # Given
        config = Config()

        # When
        result = str(config)

        # Then
        assert "test_secret" not in result
        assert "test_key" not in result
