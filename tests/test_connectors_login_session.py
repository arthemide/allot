"""The in-memory registry of logins waiting on a second factor."""

from __future__ import annotations

import pytest

from src.connectors import login_session


class Fake:
    def __init__(self, login, password):
        self.deinit_called = False

    def start(self):
        self.status = "otp"

    def deinit(self):
        self.deinit_called = True


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    monkeypatch.setattr(login_session, "factory", Fake)
    login_session.reset()
    yield
    login_session.reset()


def test_an_attempt_is_parked_and_retrievable():
    sid, attempt = login_session.begin("u", "p")
    assert login_session.get(sid) is attempt


def test_finishing_deinits_and_forgets():
    sid, attempt = login_session.begin("u", "p")
    login_session.finish(sid)
    assert attempt.deinit_called and login_session.get(sid) is None


def test_answering_an_unknown_id_raises():
    with pytest.raises(KeyError):
        login_session.answer("nope", "x")


def test_a_stale_attempt_is_swept(monkeypatch):
    sid, attempt = login_session.begin("u", "p")
    monkeypatch.setattr(login_session, "TTL_SECONDS", -1)
    login_session.begin("v", "q")  # any new begin sweeps the old one
    assert login_session.get(sid) is None and attempt.deinit_called


def test_the_default_factory_needs_woob():
    # woob is an optional dependency, absent here: the lazy import is caught
    # and surfaced as ConnectorUnavailable.
    from src.connectors.errors import ConnectorUnavailable

    with pytest.raises(ConnectorUnavailable):
        login_session._default_factory("u", "p")
