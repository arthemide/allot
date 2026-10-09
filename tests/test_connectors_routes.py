"""POST /connectors/bourso/login: the interactive sync, woob stubbed out.

No test here reaches a bank: a fake login attempt drives the state machine.
"""

from __future__ import annotations

import pytest

from src.connectors import login_session, store
from src.connectors.errors import (
    AuthenticationInterrupted,
    AuthenticationMethodUnsupported,
    AuthFailed,
    ConnectorUnavailable,
    SessionExpired,
)
from src.connectors.store import PositionRow
from src.databases import sqlite as db
from src.services import prices

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
        return type(self).rows

    def deinit(self):
        self.deinit_called = True


@pytest.fixture(autouse=True)
def fake_woob(monkeypatch, tmp_path):
    FakeLogin.script = ["done"]
    FakeLogin.rows = ROWS
    FakeLogin.raise_on_start = None
    monkeypatch.setattr(login_session, "factory", FakeLogin)
    monkeypatch.setattr(store, "DEFAULT_DB", tmp_path / "connectors.db")
    login_session.reset()
    yield
    login_session.reset()


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


class TestStraightThrough:
    def test_no_2fa_syncs_and_reports(self, client, resolver):
        # Given a login that needs no second factor
        response = post(client)
        # Then the asset is opened from the bank's figures and a snapshot is kept
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "done"
        assert body["report"]["imported"][0]["symbol"] == "CW8.PA"
        assert db.get_asset("CW8.PA")["base_quantity"] == 10.0
        assert len(store.snapshots(store.DEFAULT_DB, "bourso")) == 1

    def test_the_bank_is_authoritative(self, client, resolver):
        db.upsert_envelope("PEA", 0.0)
        db.add_asset("CW8.PA", "World", "PEA", "EUR")
        db.add_transaction("CW8.PA", "2026-01-01", "buy", 1.0, 100.0)
        post(client)
        # The manual trade is cleared: the snapshot is the whole truth
        assert db.transactions_of("CW8.PA") == []

class TestTwoFactor:
    def test_an_otp_is_asked_then_answered(self, client, resolver):
        FakeLogin.script = ["otp", "done"]
        first = post(client).json()
        assert first["status"] == "otp" and first["prompt"] == "do the thing"
        assert first["report"] is None
        second = client.post(
            f"/connectors/bourso/login/{first['session_id']}", json={"answer": "123456"}
        )
        assert second.status_code == 200
        assert second.json()["status"] == "done"
        assert db.get_asset("CW8.PA") is not None

    def test_app_validation_needs_no_code(self, client, resolver):
        FakeLogin.script = ["app_validation", "done"]
        first = post(client).json()
        assert first["status"] == "app_validation"
        done = client.post(
            f"/connectors/bourso/login/{first['session_id']}", json={}
        ).json()
        assert done["status"] == "done"

    def test_answering_an_unknown_session_is_404(self, client):
        response = client.post("/connectors/bourso/login/nope", json={"answer": "x"})
        assert response.status_code == 404


class TestFailures:
    def test_wrong_credentials_are_401(self, client):
        FakeLogin.raise_on_start = AuthFailed("bad password")
        assert post(client).status_code == 401

    def test_a_missing_woob_is_503(self, client):
        def unavailable(login, password):
            raise ConnectorUnavailable("woob is not installed")

        import src.connectors.login_session as ls

        ls.factory = unavailable
        response = post(client)
        assert response.status_code == 503
        assert "woob" in response.json()["detail"]

    def test_an_expired_app_validation_is_502(self, client, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(client).json()

        # The app validation expires: woob raises on the follow-up call
        def expired(value):
            raise SessionExpired("BoursoBank", "bourso")

        login_session.get(first["session_id"]).answer = expired
        second = client.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 502

    def test_an_interrupted_app_validation_is_502(self, client, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(client).json()

        def interrupted(value):
            raise AuthenticationInterrupted("BoursoBank rejected the validation check.")

        login_session.get(first["session_id"]).answer = interrupted
        second = client.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 502
        assert login_session.get(first["session_id"]) is None

    def test_an_unsupported_authentication_method_is_422(self, client, resolver):
        FakeLogin.script = ["app_validation"]
        first = post(client).json()

        def unsupported(value):
            raise AuthenticationMethodUnsupported("QR code is not supported")

        login_session.get(first["session_id"]).answer = unsupported
        second = client.post(f"/connectors/bourso/login/{first['session_id']}", json={})
        assert second.status_code == 422
        assert login_session.get(first["session_id"]) is None


class TestGuard:
    def test_the_route_is_behind_the_session(self, guarded_client):
        assert (
            guarded_client.post(
                "/connectors/bourso/login", json={"login": "u", "password": "p"}
            ).status_code
            == 401
        )
