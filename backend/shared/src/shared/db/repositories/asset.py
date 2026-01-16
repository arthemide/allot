from typing import List, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from shared.db.config import SessionLocal
from shared.db.models.asset import AssetTable
from shared.db.models.fund import FundTable


class AssetRepository:
    """Repository for asset CRUD operations"""

    @staticmethod
    def get_by_id(asset_id: int) -> Optional[AssetTable]:
        """Get asset by ID"""
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.id == asset_id)
            )
            asset = session.scalars(stmt).one_or_none()
        return asset

    @staticmethod
    def get_by_symbol(symbol: str, asset_type: str = "stock") -> Optional[AssetTable]:
        """Get asset by symbol and type"""
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.symbol == symbol, AssetTable.asset_type == asset_type)
            )
            asset = session.scalars(stmt).one_or_none()
        return asset

    @staticmethod
    def get_all_by_type(asset_type: str = "stock") -> List[AssetTable]:
        """Get all assets of a specific type"""
        with SessionLocal() as session:
            stmt = (
                select(AssetTable)
                .where(AssetTable.asset_type == asset_type)
                .order_by(AssetTable.symbol)
            )
            assets = session.scalars(stmt).all()
        return list(assets)

    @staticmethod
    def create(
        fund_id: Optional[int],
        name: str,
        symbol: str,
        asset_type: str,
        shares_number: float,
        cost: float,
        current_repartition: float,
        target_repartition: Optional[float] = None,
        arbitration_threshold: float = 0.0,
        threshold_to_alert: float = 0.0,
        base_prum: Optional[float] = None,
    ) -> AssetTable:
        """Create a new asset"""
        with SessionLocal() as session:
            asset = AssetTable(
                fund_id=fund_id,
                name=name,
                symbol=symbol,
                asset_type=asset_type,
                shares_number=shares_number,
                cost=cost,
                current_repartition=current_repartition,
                target_repartition=target_repartition,
                arbitration_threshold=arbitration_threshold,
                threshold_to_alert=threshold_to_alert,
                base_prum=base_prum,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)

            # Return with transactions loaded
            asset = session.scalars(
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.id == asset.id)
            ).one()

        return asset

    @staticmethod
    def update(asset_id: int, **kwargs) -> Optional[AssetTable]:
        """Update asset fields"""
        stmt = update(AssetTable).where(AssetTable.id == asset_id).values(**kwargs)
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Return updated asset
            asset = session.scalars(
                select(AssetTable)
                .options(selectinload(AssetTable.transactions))
                .where(AssetTable.id == asset_id)
            ).one_or_none()
        return asset

    @staticmethod
    def delete(asset_id: int) -> bool:
        """Delete an asset (cascade deletes transactions)"""
        stmt = delete(AssetTable).where(AssetTable.id == asset_id)
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
        return result.rowcount > 0

    @staticmethod
    def add_to_fund(fund_id: int, asset_data: dict) -> Optional[FundTable]:
        """
        Add an asset to a fund.
        This is a convenience method that maintains backward compatibility with StockRepository.add()
        """
        with SessionLocal() as session:
            with session.begin():
                asset = AssetTable(fund_id=fund_id, **asset_data)
                session.add(asset)

            # Return the fund with assets loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund

    @staticmethod
    def update_in_fund(
        fund_id: int, asset_id: int, asset_data: dict
    ) -> Optional[FundTable]:
        """
        Update an asset in a fund.
        This is a convenience method that maintains backward compatibility with StockRepository.update()
        """
        stmt = (
            update(AssetTable)
            .where(
                AssetTable.fund_id == fund_id,
                AssetTable.id == asset_id,
            )
            .values(**asset_data)
        )
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Return the fund with assets loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund

    @staticmethod
    def remove_from_fund(fund_id: int, asset_id: int) -> Optional[FundTable]:
        """
        Remove an asset from a fund.
        This is a convenience method that maintains backward compatibility with StockRepository.remove()
        """
        stmt = delete(AssetTable).where(
            AssetTable.fund_id == fund_id, AssetTable.id == asset_id
        )
        with SessionLocal() as session:
            with session.begin():
                result = session.execute(stmt)
                if result.rowcount == 0:
                    return None

            # Return the fund with assets loaded
            fund = session.scalars(
                select(FundTable)
                .options(selectinload(FundTable.assets))
                .where(FundTable.id == fund_id)
            ).one_or_none()
        return fund
