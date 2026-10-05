"""Snapshots: appended, never overwritten, in their own database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.connectors import store
from src.connectors.store import PositionRow

ROWS = [
    PositionRow(
        account="PEA",
        support_type="security",
        isin="IE00B4L5Y983",
        label="ETF",
        quantity=2.0,
        value=200.0,
        unit_cost=90.0,
        unit_price=100.0,
        gain=20.0,
    ),
    PositionRow(account="PEA", support_type="cash", label="Cash", value=12.5),
]


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "nested" / "connectors.db"


class TestSnapshots:
    def test_each_sync_adds_a_snapshot_and_keeps_the_previous_one(self, path):
        # Given two syncs, the second with the cash spent
        first = store.save_snapshot(path, "bourso", ROWS, "2026-10-01T08:00:00+00:00")
        second = store.save_snapshot(path, "bourso", ROWS[:1])
        # Then both are there, and the latest is the second
        assert [s["id"] for s in store.snapshots(path, "bourso")] == [first, second]
        latest = store.latest(path, "bourso")
        assert [row["support_type"] for row in latest] == ["security"]
        assert latest[0]["snapshot_id"] == second
        assert latest[0]["unit_cost"] == 90.0

    def test_cash_is_stored_without_isin_or_quantity(self, path):
        store.save_snapshot(path, "bourso", ROWS)
        cash = store.latest(path, "bourso")[1]
        assert (cash["isin"], cash["quantity"], cash["value"]) == (None, None, 12.5)
        assert cash["currency"] == "EUR"

    def test_sources_do_not_mix(self, path):
        store.save_snapshot(path, "bourso", ROWS)
        assert store.latest(path, "afer") == []
        assert store.snapshots(path, "afer") == []

    def test_a_failed_insert_leaves_no_half_snapshot(self, path, mocker):
        # Given a line the database refuses (no value)
        bad = PositionRow.model_construct(
            account="PEA", support_type="security", label="X", value=None
        )
        # When the snapshot is saved
        with pytest.raises(sqlite3.IntegrityError):
            store.save_snapshot(path, "bourso", [ROWS[0], bad])
        # Then nothing of it is kept
        assert store.snapshots(path, "bourso") == []
