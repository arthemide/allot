from .fund import FundTable
from .asset import AssetTable
from .transaction import AssetTransactionTable

# Backward compatibility alias
StockTable = AssetTable

__all__ = [
    "FundTable",
    "AssetTable",
    "AssetTransactionTable",
    "StockTable",  # Backward compatibility
]
