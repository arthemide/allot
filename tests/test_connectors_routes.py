"""POST /connectors/bourso/login: the interactive sync, woob stubbed out.

No test here reaches a bank: a fake login attempt drives the state machine.
The routes need the app password on, so they run on an authenticated client.
"""

from __future__ import annotations

import pytest

from src.connectors import login_session
from src.connectors.errors import (
    AuthenticationInterrupted,
    AuthenticationMethodUnsupported,
    AuthFailed,
    BankUnavailable,
    ConnectorUnavailable,
    SessionExpired,
)
from src.databases import sqlite as db
from src.models.schema import PositionRow
from src.routes import connectors as connectors_routes
from src.services import portfolio, prices

ROWS = [
    PositionRow(
        account="PEA",
        support_type="security",
        isin="IE000BI8OT95",
        label="World",
        quantity=10.0,
        value=1100.0,
        unit_cost=100.0,
        unit_price=110.0,
        gain=100.0,
    ),
    PositionRow(account="PEA", support_type="cash", label="Cash", value=20.0),
]


class FakeLogin:
    """Scripted stand-in for WoobLogin: a list of statuses to walk through."""

    script: list[str] = ["done"]
    rows: list[PositionRow] = ROWS
    raise_on_start: Exception | None = None
    raise_on_read: Exception | None = None

    def __init__(self, login: str, password: str):
        self.login, self.password = login, password
        self._steps = iter(type(self).script)
        self.status = "pending"
        self.prompt = ""
        self.deinit_called = False

    def start(self):
        if type(self).raise_on_start is not None:
            raise type(self).raise_on_start
        return self._next()

    def answer(self, value):
        self.answered = value
        return self._next()

    def _next(self):
        self.status = next(self._steps)
        self.prompt = "do the thing" if self.status != "done" else ""
        return self.status

    def investments(self):
        if type(self).raise_on_read is not None:
            raise type(self).raise_on_read
        return type(self).rows

    def deinit(self):
        self.deinit_called = True


@pytest.fixture(autouse=True)
def fake_woob(monkeypatch):
    FakeLogin.script = ["done"]
    FakeLogin.rows = ROWS
    FakeLogin.raise_on_start = None
    FakeLogin.raise_on_read = None
    monkeypatch.setattr(login_session, "factory", FakeLogin)
    login_session.reset()
    yield
    login_session.reset()


@pytest.fixture
def fresh(authenticated_client):
    """An instance with the password on, where no bank account was placed yet."""
    return authenticated_client


@pytest.fixture
def bank(fresh):
    """The same, with PEA, CTO and FUND placed in envelopes of their name."""
    for account in ("PEA", "CTO", "FUND"):
        db.upsert_envelope(account, 0.0)
        db.set_bank_account(account, account)
    return fresh


@pytest.fixture
def resolver(mocker):
    mocker.patch.object(
        prices,
        "search",
        return_value=[{"symbol": "CW8.PA", "label": "World", "currency": "EUR"}],
    )


def post(client, login="u", password="p"):
    return client.post(
        "/connectors/bourso/login", json={"login": login, "password": password}
    )


def held(symbol):
    asset = db.get_asset(symbol)
    return portfolio.position_of(asset)


class TestStraightThrough:
    def test_no_2fa_syncs_and_reports(self, bank, resolver):
        # Given a login that needs no second factor
        response = post(bank)
        # Then the asset is opened from the bank's figures
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "done"
        assert body["report"]["imported"][0]["symbol"] == "CW8.PA"
        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0

    def test_recorded_trades_are_kept_and_the_opening_absorbs_the_rest(
        self, bank, resolver
    ):
        # Given an asset with one recorded buy, the history the cash comes from
        db.add_asset("CW8.PA", "World", "PEA", "EUR")
        db.add_transaction("CW8.PA", "2026-01-01", "buy", 1.0, 100.0)
        # When the bank reports 10 units at a PRUM of 100
        post(bank)
        # Then the trade is still there, and the position is the bank's
        assert len(db.transactions_of("CW8.PA")) == 1
        position = held("CW8.PA")
        assert position["quantity"] == pytest.approx(10.0)
        assert position["prum"] == pytest.approx(100.0)

    def test_trades_holding_more_than_the_bank_are_a_conflict(self, bank, resolver):
        # Given trades that already make 12 units, an unrecorded sell since
        db.add_asset("CW8.PA", "World", "PEA", "EUR")
        db.add_transaction("CW8.PA", "2026-01-01", "buy", 12.0, 100.0)
        # When the bank reports 10
        report = post(bank).json()["report"]
        # Then nothing is touched, and the user is told why
        assert report["imported"] == []
        assert report["conflicts"] == [
            {
                "symbol": "CW8.PA",
                "label": "World",
                "bank_quantity": 10.0,
                "tracked_quantity": 12.0,
            }
        ]
        assert len(db.transactions_of("CW8.PA")) == 1
        assert held("CW8.PA")["quantity"] == 12.0

    def test_a_currency_mismatch_is_reported_unresolved(self, bank, mocker):
        FakeLogin.rows = [
            PositionRow(
                account="CTO",
                support_type="security",
                isin="US0000000001",
                label="US fund",
                quantity=2.0,
                value=200.0,
                currency="EUR",
                unit_cost=100.0,
            )
        ]
        mocker.patch.object(
            prices,
            "search",
            return_value=[{"symbol": "VTI", "label": "US fund", "currency": "USD"}],
        )

        report = post(bank).json()["report"]

        assert report["imported"] == []
        assert report["unresolved"] == [{"isin": "US0000000001", "name": "US fund"}]
        assert db.get_asset("VTI") is None

    def test_a_line_without_isin_nor_cost_is_reported_not_dropped(self, bank, mocker):
        # Given a line with parts and value but no ISIN and no cost
        FakeLogin.rows = [
            PositionRow(
                account="FUND",
                support_type="security",
                label="FUND LINE",
                quantity=4.0,
                value=200.0,
                currency="EUR",
            )
        ]
        search = mocker.patch.object(prices, "search")

        report = post(bank).json()["report"]

        # Then nothing is guessed from its label, and the user sees it
        assert report["unresolved"] == [{"isin": None, "name": "FUND LINE"}]
        search.assert_not_called()

    def test_a_cash_only_account_still_zeroes_what_was_sold(self, bank, resolver):
        # Given an asset held in the PEA
        db.add_asset("CW8.PA", "World", "PEA", "EUR")
        db.set_opening_position("CW8.PA", 3.0, 300.0)
        # When the bank now lists only cash in that account
        FakeLogin.rows = [ROWS[1]]
        post(bank)
        # Then the asset was sold off
        assert held("CW8.PA")["quantity"] == 0.0


class TestAccounts:
    def test_a_new_account_waits_for_its_envelope(self, fresh, resolver):
        # Given an account the user never placed, and an envelope of that name
        db.upsert_envelope("pea", 0.0)
        # When it syncs for the first time
        first = post(fresh).json()
        # Then nothing is written yet; the envelope of the same name is offered
        assert first["status"] == "accounts"
        assert first["accounts"] == [{"account": "PEA", "lines": 1, "envelope": "pea"}]
        assert db.get_asset("CW8.PA") is None
        # And the bank session was already let go of
        assert login_session.get(first["session_id"]).deinit_called

    def test_the_chosen_envelope_is_used_now_and_remembered(self, fresh, resolver):
        first = post(fresh).json()
        done = fresh.post(
            f"/connectors/bourso/login/{first['session_id']}/accounts",
            json={"envelopes": {"PEA": "MY PEA"}},
        ).json()
        assert done["status"] == "done"
        assert db.get_asset("CW8.PA")["envelope"] == "MY PEA"
        # The next sync goes straight through
        assert post(fresh).json()["status"] == "done"

    def test_an_account_left_out_is_skipped(self, fresh, resolver):
        first = post(fresh).json()
        done = fresh.post(
            f"/connectors/bourso/login/{first['session_id']}/accounts",
            json={"envelopes": {"PEA": None}},
        ).json()
        assert done["status"] == "done" and done["report"]["imported"] == []
        assert db.get_asset("CW8.PA") is None
        assert post(fresh).json()["status"] == "done"

    def test_every_new_account_needs_an_answer(self, fresh, resolver):
        first = post(fresh).json()
        response = fresh.post(
            f"/connectors/bourso/login/{first['session_id']}/accounts",
            json={"envelopes": {}},
        )
        assert response.status_code == 422
        assert "PEA" in response.json()["detail"]

    def test_placing_accounts_of_an_unknown_sync_is_404(self, fresh):
        response = fresh.post(
            "/connectors/bourso/login/nope/accounts", json={"envelopes": {}}
        )
        assert response.status_code == 404


class TestTwoFactor:
    def test_an_otp_is_asked_then_answered(self, bank, resolver):
        FakeLogin.script = ["otp", "done"]
        first = post(bank).json()
        assert first["status"] == "otp" and first["prompt"] == "do the thing"
        assert first["report"] is None
        second = bank.post(
            f"/connectors/bourso/login/{first['session_id']}", json={"answer": "123456"}
        )
        assert second.status_code == 200
        assert second.json()["status"] == "done"
        assert db.get_asset("CW8.PA") is not None

    def test_app_validation_needs_no_code(self, bank, resolver):
        FakeLogin.script = ["app_validation", "done"]
        first = post(bank).json()
        assert first["status"] == "app_validation"
        done = bank.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert done.json()["status"] == "done"

    def test_answering_an_unknown_session_is_404(self, bank):
        response = bank.post("/connectors/bourso/login/nope", json={"answer": "x"})
        assert response.status_code == 404


class TestFailures:
    def test_wrong_credentials_are_401(self, bank):
        FakeLogin.raise_on_start = AuthFailed("bad password")
        assert post(bank).status_code == 401

    def test_a_missing_woob_is_503(self, bank, monkeypatch):
        def unavailable(login, password):
            raise ConnectorUnavailable("woob is not installed")

        monkeypatch.setattr(login_session, "factory", unavailable)
        response = post(bank)
        assert response.status_code == 503
        assert "woob" in response.json()["detail"]

    def test_a_bank_that_cannot_be_read_is_502_and_writes_nothing(self, bank):
        FakeLogin.raise_on_read = BankUnavailable("BoursoBank could not be read.")
        response = post(bank)
        assert response.status_code == 502
        assert db.all_assets() == []

    def test_an_expired_app_validation_is_502(self, bank, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(bank).json()

        # The app validation expires: woob raises on the follow-up call
        def expired(value):
            raise SessionExpired("BoursoBank")

        login_session.get(first["session_id"]).answer = expired
        second = bank.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 502

    def test_an_interrupted_app_validation_is_502(self, bank, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(bank).json()

        def interrupted(value):
            raise AuthenticationInterrupted("BoursoBank rejected the validation check.")

        login_session.get(first["session_id"]).answer = interrupted
        second = bank.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 502
        assert login_session.get(first["session_id"]) is None

    def test_an_unsupported_authentication_method_is_422(self, bank, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(bank).json()

        def unsupported(value):
            raise AuthenticationMethodUnsupported("QR code is not supported")

        login_session.get(first["session_id"]).answer = unsupported
        second = bank.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 422
        assert login_session.get(first["session_id"]) is None


class TestGuard:
    def test_the_route_is_behind_the_session(self, guarded_client):
        response = post(guarded_client)
        assert response.status_code == 401

    def test_an_instance_without_a_password_refuses_bank_credentials(self, client):
        response = post(client)
        assert response.status_code == 403
        assert "ALLOT_PASSWORD_HASH" in response.json()["detail"]

    def test_bank_logins_are_capped(self, bank, resolver):
        for _ in range(connectors_routes.LOGIN_LIMIT):
            assert post(bank).status_code == 200
        response = post(bank)
        assert response.status_code == 429
        assert "Retry-After" in response.headers
