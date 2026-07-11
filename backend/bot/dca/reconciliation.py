"""
Reconciliation between the local position and the Binance spot balance.

The local DB only records purchases made by the bot (plus a manual historical
seed), so any sell/withdrawal/conversion done outside the bot makes the two
drift apart silently. This job compares both sides and raises an email alert
when the difference exceeds a tolerance, instead of letting the PRUM and P&L
become wrong without anyone noticing.
"""

from decimal import Decimal

from loguru import logger

from shared.db.repositories.transaction import TransactionRepository

from .binance_client import BinanceAPIError, BinanceClient
from .config import Config
from .email_notifier import get_notifier

# Maximum tolerated difference (in base asset units) before alerting
TOLERANCE = Decimal("0.0001")


def reconcile_balance(client: BinanceClient, config: Config) -> bool:
    """
    Compare the locally tracked quantity with the Binance spot balance.

    Args:
        client: Configured Binance client
        config: Bot configuration

    Returns:
        True if local and broker quantities match within tolerance
    """
    dca_config = config.dca
    base_asset = dca_config.base_asset
    tolerance = TOLERANCE

    local_qty = TransactionRepository.calculate_total_quantity(
        dca_config.asset_symbol
    )
    if local_qty is None:
        logger.warning(
            f"Reconciliation skipped: asset {dca_config.asset_symbol} not found in DB"
        )
        return True

    try:
        balance = client.get_asset_balance(base_asset)
    except BinanceAPIError as e:
        logger.error(f"Reconciliation failed: cannot fetch {base_asset} balance: {e}")
        get_notifier().notify_error("Reconciliation Error", str(e))
        return False

    broker_qty = balance.total
    drift = broker_qty - local_qty

    logger.info(
        f"Reconciliation {base_asset}: local={local_qty}, broker={broker_qty}, "
        f"drift={drift} (tolerance={tolerance})"
    )

    if abs(drift) > tolerance:
        logger.warning(
            f"⚠️ Position drift detected for {base_asset}: "
            f"local={local_qty}, broker={broker_qty}, drift={drift}"
        )
        get_notifier().notify_reconciliation_drift(
            asset=base_asset,
            local_qty=str(local_qty),
            broker_qty=str(broker_qty),
            drift=str(drift),
        )
        return False

    logger.info(f"✅ Reconciliation OK for {base_asset}")
    return True
