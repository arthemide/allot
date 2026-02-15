"""
Tests for AssetRepository — CRUD operations on assets and fund-asset relations.
"""

from shared.db.repositories.asset import AssetRepository
from shared.db.repositories.fund import FundRepository

ASSET_DEFAULTS = dict(
    name="Ethereum",
    symbol="ETHUSDC",
    asset_type="crypto",
    shares_number=1.0,
    cost=2000.0,
    current_repartition=0.0,
    arbitration_threshold=0.0,
    threshold_to_alert=0.0,
)


class TestAssetCRUD:
    """Tests for basic asset CRUD operations."""

    def test_create(self, mock_session_local):
        """
        Given: Valid asset data
        When: create(...)
        Then: Returns created asset with transactions loaded
        """
        asset = AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)

        assert asset is not None
        assert asset.symbol == "ETHUSDC"
        assert asset.name == "Ethereum"
        assert asset.id is not None
        assert asset.transactions == []

    def test_get_by_id(self, mock_session_local):
        """
        Given: Asset exists
        When: get_by_id(id)
        Then: Returns the asset
        """
        created = AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)

        result = AssetRepository.get_by_id(created.id)

        assert result is not None
        assert result.symbol == "ETHUSDC"

    def test_get_by_id_not_found(self, mock_session_local):
        """
        Given: No asset with given ID
        When: get_by_id(id)
        Then: Returns None
        """
        result = AssetRepository.get_by_id(9999)
        assert result is None

    def test_get_by_symbol(self, mock_session_local):
        """
        Given: Asset exists with symbol and type
        When: get_by_symbol(symbol, asset_type)
        Then: Returns the asset
        """
        AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)

        result = AssetRepository.get_by_symbol("ETHUSDC", asset_type="crypto")

        assert result is not None
        assert result.symbol == "ETHUSDC"

    def test_get_by_symbol_not_found(self, mock_session_local):
        """
        Given: No asset with given symbol
        When: get_by_symbol(symbol)
        Then: Returns None
        """
        result = AssetRepository.get_by_symbol("NONEXIST", asset_type="crypto")
        assert result is None

    def test_get_all_by_type(self, mock_session_local):
        """
        Given: Multiple assets of different types
        When: get_all_by_type(type)
        Then: Returns only matching assets
        """
        AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)
        AssetRepository.create(
            fund_id=None,
            name="Apple",
            symbol="AAPL",
            asset_type="stock",
            shares_number=10.0,
            cost=1500.0,
            current_repartition=0.0,
        )

        crypto = AssetRepository.get_all_by_type("crypto")
        stocks = AssetRepository.get_all_by_type("stock")

        assert len(crypto) == 1
        assert crypto[0].symbol == "ETHUSDC"
        assert len(stocks) == 1
        assert stocks[0].symbol == "AAPL"

    def test_update(self, mock_session_local):
        """
        Given: Asset exists
        When: update(id, name=new_name)
        Then: Returns updated asset
        """
        created = AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)

        result = AssetRepository.update(created.id, name="Updated Name")

        assert result is not None
        assert result.name == "Updated Name"

    def test_update_not_found(self, mock_session_local):
        """
        Given: No asset with given ID
        When: update(id, name=x)
        Then: Returns None
        """
        result = AssetRepository.update(9999, name="X")
        assert result is None

    def test_delete(self, mock_session_local):
        """
        Given: Asset exists
        When: delete(id)
        Then: Returns True
        """
        created = AssetRepository.create(fund_id=None, **ASSET_DEFAULTS)

        result = AssetRepository.delete(created.id)

        assert result is True
        assert AssetRepository.get_by_id(created.id) is None

    def test_delete_not_found(self, mock_session_local):
        """
        Given: No asset with given ID
        When: delete(id)
        Then: Returns False
        """
        result = AssetRepository.delete(9999)
        assert result is False


class TestAssetFundOperations:
    """Tests for asset-fund relationship operations."""

    def test_add_to_fund(self, mock_session_local):
        """
        Given: Fund exists
        When: add_to_fund(fund_id, asset_data)
        Then: Returns fund with the new asset
        """
        fund = FundRepository.create("Test Fund")

        result = AssetRepository.add_to_fund(fund.id, ASSET_DEFAULTS)

        assert result is not None
        assert len(result.assets) == 1
        assert result.assets[0].symbol == "ETHUSDC"

    def test_update_in_fund(self, mock_session_local):
        """
        Given: Fund with asset
        When: update_in_fund(fund_id, asset_id, new_data)
        Then: Returns fund with updated asset
        """
        fund = FundRepository.create("Test Fund")
        fund_with_asset = AssetRepository.add_to_fund(fund.id, ASSET_DEFAULTS)
        asset_id = fund_with_asset.assets[0].id

        result = AssetRepository.update_in_fund(
            fund.id, asset_id, {"name": "Updated ETH"}
        )

        assert result is not None
        assert result.assets[0].name == "Updated ETH"

    def test_update_in_fund_not_found(self, mock_session_local):
        """
        Given: No matching asset in fund
        When: update_in_fund(fund_id, bad_id, data)
        Then: Returns None
        """
        fund = FundRepository.create("Test Fund")

        result = AssetRepository.update_in_fund(fund.id, 9999, {"name": "X"})

        assert result is None

    def test_remove_from_fund(self, mock_session_local):
        """
        Given: Fund with asset
        When: remove_from_fund(fund_id, asset_id)
        Then: Returns fund without the asset
        """
        fund = FundRepository.create("Test Fund")
        fund_with_asset = AssetRepository.add_to_fund(fund.id, ASSET_DEFAULTS)
        asset_id = fund_with_asset.assets[0].id

        result = AssetRepository.remove_from_fund(fund.id, asset_id)

        assert result is not None
        assert len(result.assets) == 0

    def test_remove_from_fund_not_found(self, mock_session_local):
        """
        Given: No matching asset in fund
        When: remove_from_fund(fund_id, bad_id)
        Then: Returns None
        """
        fund = FundRepository.create("Test Fund")

        result = AssetRepository.remove_from_fund(fund.id, 9999)

        assert result is None
