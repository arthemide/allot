"""The woob backend behind the BoursoBank sync. Only file that imports woob.

woob performs the login itself - virtual keyboard, strong authentication, the
lot - and we drive it: hand it the credentials, answer the one challenge it
raises, then read the investments. Nothing here reimplements the bank's login.

Not unit-tested: it needs woob installed and the modules vendored. The login
state machine around it (login_session.py) is what the tests exercise, through
an injected fake. Kept out of coverage for the same reason as browser.py.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from src.connectors.errors import AuthFailed, ConnectorUnavailable, SessionExpired
from src.connectors.paths import ROOT, STATE_DIR
from src.connectors.store import PositionRow

logger = logging.getLogger(__name__)


def _unavailable() -> "ConnectorUnavailable":
    return ConnectorUnavailable(
        "woob is not installed in this image. Build it with INSTALL_WOOB=1 "
        "(or `make woob-install` for a local run)."
    )


MODULE = "boursorama"
# Vendored modules, so nothing is fetched at runtime; STATE_DIR holds the
# 90-day trusted-device cookie.
MODULES_PATH = ROOT / "vendor" / "woob-modules"


class WoobLogin:
    """One login attempt and the sync that follows it.

    `status` moves through "otp" / "app_validation" while the bank asks for a
    second factor, then "done" once the backend is usable, or raises.
    """

    def __init__(self, login: str, password: str):
        try:
            # WoobBase, not Woob: it loads modules straight from a directory,
            # with no repository and no `woob update`, so nothing is ever
            # fetched over the network. The module must be vendored.
            from woob.core import WoobBase
        except ImportError:  # older layout
            try:
                from woob.core.ouiboube import WoobBase
            except ModuleNotFoundError as error:
                raise _unavailable() from error
        except ModuleNotFoundError as error:  # the connectors group is optional
            raise _unavailable() from error

        if not (MODULES_PATH / MODULE).is_dir():
            raise ConnectorUnavailable(
                f"the woob '{MODULE}' module is not vendored under {MODULES_PATH}. "
                "Run `make woob-vendor` from a machine that has it."
            )

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._woob = WoobBase(modules_path=str(MODULES_PATH))
        self._login = login
        self._password = password
        self._backend: Any = None
        self.status = "pending"
        self.prompt = ""

    # --- login -----------------------------------------------------------

    def start(self) -> str:
        return self._attempt({})

    def answer(self, value: str) -> str:
        """Supply the code, or acknowledge the app validation, and resume."""
        if self.status == "app_validation":
            return self._attempt({})
        return self._attempt({self._field: value})

    def _attempt(self, extra: dict[str, str]) -> str:
        from woob.exceptions import (
            AppValidationExpired,
            BrowserIncorrectPassword,
            BrowserQuestion,
            DecoupledValidation,
        )

        params = {"login": self._login, "password": self._password, **self._stored}
        try:
            self._backend = self._woob.build_backend(
                MODULE, params=params, name="allot"
            )
            self._backend.browser.dump_state()  # trust the device for next time
            self.status = "done"
            self.prompt = ""
        except BrowserQuestion as question:
            field = question.fields[0]
            self._field = field.id
            self._stored = params
            self.status = "otp"
            self.prompt = field.label or "Enter the code the bank sent you."
        except DecoupledValidation as validation:
            self._stored = params
            self.status = "app_validation"
            self.prompt = str(validation.message) or "Validate in your bank app."
        except AppValidationExpired:
            self.status = "failed"
            raise SessionExpired("BoursoBank", "bourso") from None
        except BrowserIncorrectPassword as error:
            self.status = "failed"
            raise AuthFailed(str(error)) from None
        return self.status

    # --- reading ---------------------------------------------------------

    def investments(self) -> list[PositionRow]:
        from woob.capabilities.bank import Account

        # Every securities account: PEA, PEA-PME and plain ones (CTO, CEFP).
        # Each keeps its own label as its envelope, so they never mix.
        wanted = {
            getattr(Account, name)
            for name in ("TYPE_PEA", "TYPE_PEA_PME", "TYPE_MARKET")
            if hasattr(Account, name)
        }
        rows: list[PositionRow] = []
        for account in self._backend.iter_accounts():
            label = str(getattr(account, "label", "") or account.id)
            logger.info(
                "woob account %s type=%s wanted=%s",
                label,
                account.type,
                account.type in wanted,
            )
            if account.type not in wanted:
                continue
            # The account's own label is the envelope ("PEA", "CTO", "CEFP").
            name = label
            account_rows = list(
                self._rows(name, self._backend.iter_investment(account))
            )
            logger.info("woob account %s -> %d investment(s)", label, len(account_rows))
            rows.extend(account_rows)
        return rows

    @staticmethod
    def _rows(account: str, investments: Iterator[Any]) -> Iterator[PositionRow]:
        for inv in investments:
            value = _number(inv.valuation)
            if value is None:
                continue
            label = str(inv.label)
            if _is_cash(inv):
                yield PositionRow(
                    account=account, support_type="cash", label=label, value=value
                )
                continue
            yield PositionRow(
                account=account,
                support_type="security",
                isin=_text(inv.code) if _text(inv.code) else None,
                label=label,
                quantity=_number(inv.quantity),
                value=value,
                unit_cost=_number(inv.unitprice),
                unit_price=_number(inv.unitvalue),
                gain=_number(inv.diff),
            )

    def deinit(self) -> None:
        try:
            if self._backend is not None:
                self._backend.deinit()
        finally:
            self._backend = None

    _field = ""
    _stored: dict[str, str] = {}


def _is_cash(inv: Any) -> bool:
    return str(getattr(inv, "code", "") or "").upper() in ("", "XX-LIQUIDITY", "LIQ")


def _text(value: Any) -> str:
    from woob.capabilities.base import empty

    return "" if value is None or empty(value) else str(value)


def _number(value: Any) -> float | None:
    from woob.capabilities.base import empty

    if value is None or empty(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
