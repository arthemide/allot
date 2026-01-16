from .asset import AssetRepository
from .fund import FundRepository
from .transaction import TransactionRepository

# Backward compatibility alias
StockRepository = AssetRepository

__all__ = [
    "FundRepository",
    "AssetRepository",
    "TransactionRepository",
    "StockRepository",  # Backward compatibility
]
