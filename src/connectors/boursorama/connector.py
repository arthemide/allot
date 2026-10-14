"""The woob backend behind the BoursoBank sync. Only file that imports woob.

woob performs the login itself - virtual keyboard, strong authentication, the
lot - and we drive it: hand it the credentials, answer the one challenge it
raises, then read the investments. Nothing here reimplements the bank's login.

Tested with woob stubbed out in sys.modules (tests/test_connectors_boursorama.py), so
neither woob nor the vendored module is needed to run the suite.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator

from src.connectors.errors import (
    AuthenticationInterrupted,
    AuthenticationMethodUnsupported,
    AuthFailed,
    BankUnavailable,
    ConnectorUnavailable,
    SessionExpired,
)
from src.connectors.paths import DATA_DIR, ROOT
from src.models.schema import PositionRow

logger = logging.getLogger(__name__)


def _unavailable() -> "ConnectorUnavailable":
    return ConnectorUnavailable(
        "woob is not installed in this image. Build it with INSTALL_WOOB=1 "
        "(or `make woob-install` for a local run)."
    )


MODULE = "boursorama"
# Vendored modules, so nothing is fetched at runtime.
MODULES_PATH = ROOT / "vendor" / "woob-modules"
# woob's saved state: the 90-day trusted-device cookie, a secret.
STATE_DIR = DATA_DIR / "woob-state"


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
            from woob.tools.storage import StandardStorage
        except ImportError:  # older layout
            try:
                from woob.core.ouiboube import WoobBase
                from woob.tools.storage import StandardStorage
            except ModuleNotFoundError as error:
                raise _unavailable() from error
        except ModuleNotFoundError as error:  # the woob group is optional
            raise _unavailable() from error

        if not (MODULES_PATH / MODULE).is_dir():
            raise ConnectorUnavailable(
                f"the woob '{MODULE}' module is not vendored under {MODULES_PATH}. "
                "Restore it from git, or run `make woob-update`."
            )

        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._storage = StandardStorage(STATE_DIR / "boursorama.yml")
        self._woob = WoobBase(modules_path=str(MODULES_PATH), storage=self._storage)
        self._login = login
        self._password = password
        self._backend: Any = None
        self.status = "pending"
        self.prompt = ""

    # --- login -----------------------------------------------------------

    def start(self) -> str:
        return self._attempt()

    def answer(self, value: str) -> str:
        """Supply the code, or acknowledge the app validation, and resume."""
        if self.status == "app_validation":
            self._backend.config["resume"].set(True)
        else:
            self._backend.config[self._field].set(value)
        return self._attempt()

    def _attempt(self) -> str:
        from woob.browser.exceptions import ClientError
        from woob.exceptions import (
            ActionNeeded,
            AppValidationError,
            AuthMethodNotImplemented,
            BrowserIncorrectPassword,
            BrowserQuestion,
            BrowserUnavailable,
            DecoupledValidation,
        )

        try:
            if self._backend is None:
                # Woob refuses an MFA flow without this explicit acknowledgement
                # that a caller can show the user its interactive challenge.
                self._backend = self._woob.build_backend(
                    MODULE,
                    params={
                        "login": self._login,
                        "password": self._password,
                        "request_information": True,
                    },
                    storage=self._storage,
                    name="allot",
                )
            self._backend.browser.do_login()
            self._backend.dump_state()  # trust the device for next time
            self.status = "done"
            self.prompt = ""
        except BrowserQuestion as question:
            field = question.fields[0]
            self._field = field.id
            self.status = "otp"
            self.prompt = field.label or "Enter the code the bank sent you."
        except DecoupledValidation as validation:
            self.status = "app_validation"
            self.prompt = str(validation.message) or "Validate in your bank app."
        except AppValidationError:
            # Expired, or refused in the bank app.
            self.status = "failed"
            raise SessionExpired("BoursoBank") from None
        except BrowserIncorrectPassword as error:
            self.status = "failed"
            raise AuthFailed(str(error)) from None
        except AuthMethodNotImplemented as error:
            self.status = "failed"
            logger.warning(
                "BoursoBank requested QR validation; safe response shape: %s",
                _shape(
                    getattr(getattr(self._backend.browser, "page", None), "doc", None)
                ),
            )
            raise AuthenticationMethodUnsupported(
                "BoursoBank requires QR-code validation, which Woob does not support. "
                "Import the BoursoBank CSV export instead."
            ) from error
        except ClientError as error:
            self.status = "failed"
            if getattr(error.response, "status_code", None) == 401:
                raise AuthenticationInterrupted(
                    "BoursoBank rejected the validation check. Start the connection again."
                ) from None
            raise AuthenticationInterrupted(
                "BoursoBank interrupted the connection. Start it again."
            ) from error
        except ActionNeeded as error:
            # New terms to accept, a password to renew: only the website can.
            self.status = "failed"
            raise BankUnavailable(
                "BoursoBank asks for an action on its website first. Log in "
                "there, then sync again."
            ) from error
        except BrowserUnavailable as error:
            self.status = "failed"
            raise BankUnavailable(
                "BoursoBank is unavailable right now. Try again later."
            ) from error
        return self.status

    # --- reading ---------------------------------------------------------

    def investments(self) -> list[PositionRow]:
        """Every security and cash line of the securities accounts.

        Anything woob raises while reading - the bank down, a page it no
        longer understands - becomes BankUnavailable: the sync stops before
        anything is written.
        """
        try:
            return self._investments()
        except Exception as error:
            logger.exception("woob failed while reading the BoursoBank accounts")
            raise BankUnavailable(
                "BoursoBank could not be read. Try again later; if it keeps "
                "failing, the woob module may need a refresh."
            ) from error

    def _investments(self) -> list[PositionRow]:
        from woob.capabilities.bank import Account

        # Every securities account: PEA, PEA-PME and plain securities accounts.
        # Each is placed in an envelope by the user, the first time it shows up.
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
            account_rows = list(
                self._rows(label, self._backend.iter_investment(account))
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
            isin = _text(inv.code) if _text(inv.code) else None
            quantity = _number(inv.quantity)
            gain = _number(inv.diff)
            unit_cost = _number(inv.unitprice)
            if unit_cost is None and gain is not None and quantity:
                # No cost column, but the latent gain gives it back.
                unit_cost = (value - gain) / quantity
            # Which fields the bank filled, never their values: enough to tell
            # why a line ends up unresolved.
            logger.info(
                "woob line in %s: isin=%s quantity=%s cost=%s",
                account,
                isin is not None,
                quantity is not None,
                unit_cost is not None,
            )
            yield PositionRow(
                account=account,
                support_type="security",
                isin=isin,
                label=label,
                quantity=quantity,
                value=value,
                unit_cost=unit_cost,
                unit_price=_number(inv.unitvalue),
                gain=gain,
            )

    def deinit(self) -> None:
        try:
            if self._backend is not None:
                self._backend.deinit()
        finally:
            self._backend = None

    _field = ""


def _is_cash(inv: Any) -> bool:
    code = str(getattr(inv, "code", "") or "").upper()
    if code in ("XX-LIQUIDITY", "LIQ"):
        return True
    # A holding reported with a quantity is a security even without an ISIN,
    # not a cash balance.
    quantity = _number(getattr(inv, "quantity", None))
    return code == "" and not (quantity is not None and quantity > 0)


def _shape(value: Any) -> Any:
    """Describe an authentication response without logging its contents."""
    if isinstance(value, dict):
        return {str(key): _shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_shape(item) for item in value[:3]]
    if isinstance(value, str):
        return f"string({len(value)})"
    return type(value).__name__


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
