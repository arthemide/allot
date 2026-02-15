"""
Tests for FundRepository — CRUD operations on funds.
"""

from shared.db.repositories.fund import FundRepository


class TestFundRepository:
    """Tests for FundRepository with patched SessionLocal."""

    def test_get_all_returns_funds(self, mock_session_local):
        """
        Given: Two funds exist
        When: get_all()
        Then: Returns list of FundTable
        """
        # Given
        FundRepository.create("Fund A")
        FundRepository.create("Fund B")

        # When
        result = FundRepository.get_all()

        # Then
        assert len(result) == 2

    def test_get_all_empty(self, mock_session_local):
        """
        Given: No funds
        When: get_all()
        Then: Returns empty list
        """
        result = FundRepository.get_all()
        assert result == []

    def test_get_by_id(self, mock_session_local):
        """
        Given: Fund exists
        When: get_by_id(id)
        Then: Returns the fund
        """
        # Given
        fund = FundRepository.create("My Fund")

        # When
        result = FundRepository.get_by_id(str(fund.id))

        # Then
        assert result is not None
        assert result.name == "My Fund"

    def test_get_by_id_not_found(self, mock_session_local):
        """
        Given: No fund with given ID
        When: get_by_id(id)
        Then: Returns None
        """
        result = FundRepository.get_by_id("9999")
        assert result is None

    def test_create(self, mock_session_local):
        """
        Given: Valid fund name
        When: create(name)
        Then: Returns created FundTable with assets loaded
        """
        result = FundRepository.create("New Fund")

        assert result is not None
        assert result.name == "New Fund"
        assert result.id is not None
        assert result.assets == []

    def test_update(self, mock_session_local):
        """
        Given: Fund exists
        When: update(id, name)
        Then: Returns updated fund
        """
        # Given
        fund = FundRepository.create("Original")

        # When
        result = FundRepository.update(str(fund.id), name="Updated")

        # Then
        assert result is not None
        assert result.name == "Updated"

    def test_update_not_found(self, mock_session_local):
        """
        Given: No fund with given ID
        When: update(id, name)
        Then: Returns None
        """
        result = FundRepository.update("9999", name="X")
        assert result is None

    def test_delete(self, mock_session_local):
        """
        Given: Fund exists
        When: delete(id)
        Then: Returns True and fund is removed
        """
        # Given
        fund = FundRepository.create("To Delete")

        # When
        result = FundRepository.delete(str(fund.id))

        # Then
        assert result is True
        assert FundRepository.get_by_id(str(fund.id)) is None
