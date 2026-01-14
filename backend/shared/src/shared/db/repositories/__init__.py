from .fund import FundRepository
from .asset import AssetRepository
from .transaction import TransactionRepository

# Backward compatibility alias
StockRepository = AssetRepository

__all__ = [
    "FundRepository",
    "AssetRepository",
    "TransactionRepository",
    "StockRepository",  # Backward compatibility
]
