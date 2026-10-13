"""The thin adapter that drives Woob's interactive BoursoBank login."""

from __future__ import annotations

import sys
import types

import pytest

from src.connectors import woob_bourso


class _Question(Exception):
    def __init__(self, field):
        self.fields = [field]


class _Validation(Exception):
    def __init__(self, message=""):
        self.message = message


class _Value:
    def __init__(self):
        self.value = None

    def set(self, value):
        self.value = value


class _Browser:
    def __init__(self):
        self.calls = 0

    def do_login(self):
        self.calls += 1
        if self.calls == 1:
            raise _Question(types.SimpleNamespace(id="code", label="SMS code"))


class _Backend:
    def __init__(self):
        self.browser = _Browser()
        self.config = {"code": _Value(), "resume": _Value()}
        self.dumped = False

    def dump_state(self):
        self.dumped = True

    def deinit(self):
        pass


class _Woob:
    backend = _Backend()
    build_params = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def build_backend(self, module, **kwargs):
        type(self).build_params = kwargs["params"]
        return type(self).backend


class _ClientError(Exception):
    def __init__(self, status_code):
        self.response = types.SimpleNamespace(status_code=status_code)


class _Unsupported(Exception):
    pass


def test_shape_never_contains_authentication_values():
    assert woob_bourso._shape(
        {"qrcode": "secret-qr-payload", "items": [123, True]}
    ) == {"qrcode": "string(17)", "items": ["int", "bool"]}


def test_login_drives_one_interactive_browser(monkeypatch, tmp_path):
    core = types.ModuleType("woob.core")
    core.WoobBase = _Woob
    exceptions = types.ModuleType("woob.exceptions")
    exceptions.AppValidationError = type("AppValidationError", (Exception,), {})
    exceptions.ActionNeeded = type("ActionNeeded", (Exception,), {})
    exceptions.BrowserUnavailable = type("BrowserUnavailable", (Exception,), {})
    exceptions.AuthMethodNotImplemented = _Unsupported
    exceptions.BrowserIncorrectPassword = type(
        "BrowserIncorrectPassword", (Exception,), {}
    )
    exceptions.BrowserQuestion = _Question
    exceptions.DecoupledValidation = _Validation
    storage = types.ModuleType("woob.tools.storage")
    storage.StandardStorage = lambda path: path
    browser_exceptions = types.ModuleType("woob.browser.exceptions")
    browser_exceptions.ClientError = _ClientError
    monkeypatch.setitem(sys.modules, "woob.core", core)
    monkeypatch.setitem(sys.modules, "woob.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "woob.tools.storage", storage)
    monkeypatch.setitem(sys.modules, "woob.browser.exceptions", browser_exceptions)
    monkeypatch.setattr(woob_bourso, "STATE_DIR", tmp_path)
    _Woob.backend = _Backend()

    login = woob_bourso.WoobLogin("123456", "password")

    assert login.start() == "otp"
    assert login.answer("654321") == "done"
    assert _Woob.build_params["request_information"] is True
    assert _Woob.backend.browser.calls == 2
    assert _Woob.backend.config["code"].value == "654321"
    assert _Woob.backend.dumped


def test_rejected_app_validation_is_a_clean_login_failure(monkeypatch, tmp_path):
    class RejectedBrowser:
        def do_login(self):
            raise _ClientError(401)

    core = types.ModuleType("woob.core")
    core.WoobBase = _Woob
    exceptions = types.ModuleType("woob.exceptions")
    exceptions.AppValidationError = type("AppValidationError", (Exception,), {})
    exceptions.ActionNeeded = type("ActionNeeded", (Exception,), {})
    exceptions.BrowserUnavailable = type("BrowserUnavailable", (Exception,), {})
    exceptions.AuthMethodNotImplemented = _Unsupported
    exceptions.BrowserIncorrectPassword = type(
        "BrowserIncorrectPassword", (Exception,), {}
    )
    exceptions.BrowserQuestion = _Question
    exceptions.DecoupledValidation = _Validation
    storage = types.ModuleType("woob.tools.storage")
    storage.StandardStorage = lambda path: path
    browser_exceptions = types.ModuleType("woob.browser.exceptions")
    browser_exceptions.ClientError = _ClientError
    monkeypatch.setitem(sys.modules, "woob.core", core)
    monkeypatch.setitem(sys.modules, "woob.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "woob.tools.storage", storage)
    monkeypatch.setitem(sys.modules, "woob.browser.exceptions", browser_exceptions)
    monkeypatch.setattr(woob_bourso, "STATE_DIR", tmp_path)
    _Woob.backend = _Backend()
    _Woob.backend.browser = RejectedBrowser()

    login = woob_bourso.WoobLogin("123456", "password")

    from src.connectors.errors import AuthenticationInterrupted

    with pytest.raises(AuthenticationInterrupted, match="rejected the validation"):
        login.start()


def test_qr_code_validation_is_reported_as_unsupported(monkeypatch, tmp_path):
    class QrCodeBrowser:
        def do_login(self):
            raise _Unsupported()

    core = types.ModuleType("woob.core")
    core.WoobBase = _Woob
    exceptions = types.ModuleType("woob.exceptions")
    exceptions.AppValidationError = type("AppValidationError", (Exception,), {})
    exceptions.ActionNeeded = type("ActionNeeded", (Exception,), {})
    exceptions.BrowserUnavailable = type("BrowserUnavailable", (Exception,), {})
    exceptions.AuthMethodNotImplemented = _Unsupported
    exceptions.BrowserIncorrectPassword = type(
        "BrowserIncorrectPassword", (Exception,), {}
    )
    exceptions.BrowserQuestion = _Question
    exceptions.DecoupledValidation = _Validation
    storage = types.ModuleType("woob.tools.storage")
    storage.StandardStorage = lambda path: path
    browser_exceptions = types.ModuleType("woob.browser.exceptions")
    browser_exceptions.ClientError = _ClientError
    monkeypatch.setitem(sys.modules, "woob.core", core)
    monkeypatch.setitem(sys.modules, "woob.exceptions", exceptions)
    monkeypatch.setitem(sys.modules, "woob.tools.storage", storage)
    monkeypatch.setitem(sys.modules, "woob.browser.exceptions", browser_exceptions)
    monkeypatch.setattr(woob_bourso, "STATE_DIR", tmp_path)
    _Woob.backend = _Backend()
    _Woob.backend.browser = QrCodeBrowser()

    login = woob_bourso.WoobLogin("123456", "password")

    from src.connectors.errors import AuthenticationMethodUnsupported

    with pytest.raises(AuthenticationMethodUnsupported, match="QR-code"):
        login.start()


def _stub_empty(monkeypatch):
    base = types.ModuleType("woob.capabilities.base")
    base.empty = lambda value: value is None
    monkeypatch.setitem(sys.modules, "woob.capabilities.base", base)


@pytest.mark.parametrize(
    "code, quantity, cash",
    [
        ("XX-LIQUIDITY", None, True),
        ("", None, True),
        # A part-based line without ISIN, as a CEFP shows it, is a support.
        ("", 5.0, False),
        ("FR0010315770", 5.0, False),
    ],
)
def test_only_a_balance_without_parts_is_cash(monkeypatch, code, quantity, cash):
    _stub_empty(monkeypatch)
    inv = types.SimpleNamespace(code=code, quantity=quantity)
    assert woob_bourso._is_cash(inv) is cash


def test_the_cost_basis_is_derived_from_the_latent_gain(monkeypatch):
    _stub_empty(monkeypatch)
    inv = types.SimpleNamespace(
        code="FR0010315770",
        label="Fund",
        quantity=4.0,
        valuation=640.0,
        unitprice=None,
        unitvalue=160.0,
        diff=40.0,
    )
    (row,) = woob_bourso.WoobLogin._rows("CEFP", iter([inv]))
    assert row.unit_cost == 150.0


def test_a_bank_that_fails_while_read_stops_the_sync(monkeypatch):
    bank = types.ModuleType("woob.capabilities.bank")
    bank.Account = types.SimpleNamespace(TYPE_PEA="pea")
    monkeypatch.setitem(sys.modules, "woob.capabilities.bank", bank)

    class Down:
        def iter_accounts(self):
            raise RuntimeError("502 from the bank")

    login = woob_bourso.WoobLogin.__new__(woob_bourso.WoobLogin)
    login._backend = Down()

    from src.connectors.errors import BankUnavailable

    with pytest.raises(BankUnavailable, match="could not be read"):
        login.investments()
