"""Single-user authentication: a password, and a signed session cookie.

Stdlib only: the target is a 32-bit Raspberry Pi, where a dependency without
an armv7 wheel has to be compiled.

Authentication is off unless ALLOT_PASSWORD_HASH is set, so the LAN
arrangement keeps working as before.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

COOKIE_NAME = "allot_session"

# 2**14 rather than the 2**17 a server would use: on a 900 MHz ARMv7 the
# higher setting costs seconds per login.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def password_hash() -> str:
    return os.getenv("ALLOT_PASSWORD_HASH", "").strip()


def enabled() -> bool:
    return bool(password_hash())


def feed_token() -> str:
    """The token that opens the calendar feed, or empty when there is none.

    A calendar client cannot log in, so the feed is opened by a secret carried
    in the URL - which makes that URL the credential. Unset: the feed stays
    behind the session like every other route.
    """
    return os.getenv("ALLOT_FEED_TOKEN", "").strip()


def feed_token_valid(candidate: str) -> bool:
    token = feed_token()
    return bool(token) and secrets.compare_digest(candidate, token)


def session_days() -> int:
    return int(os.getenv("ALLOT_SESSION_DAYS", "30"))


def cookie_secure() -> bool:
    return os.getenv("ALLOT_COOKIE_SECURE", "1") not in ("0", "false", "no", "")


def secret_key() -> bytes:
    """The key session cookies are signed with.

    Missing is a hard error: a key generated on the spot would look like it
    works and then log everyone out on the next restart.
    """
    key = os.getenv("ALLOT_SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ALLOT_SECRET_KEY is required when ALLOT_PASSWORD_HASH is set. "
            "Generate one with: python -c "
            "'import secrets; print(secrets.token_urlsafe(32))'"
        )
    return key.encode()


def hash_password(password: str) -> str:
    """Encode a password as `scrypt$n$r$p$salt$key`, salt and key in base64."""
    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_BYTES,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(key)}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash.

    The parameters are read back from the string, so hashes produced with
    older settings keep working after they change.
    """
    try:
        scheme, n, r, p, salt, key = encoded.split("$")
        if scheme != "scrypt":
            return False
        computed = hashlib.scrypt(
            password.encode(),
            salt=_unb64(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(_unb64(key)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, _unb64(key))


def _signature(payload: str) -> str:
    return _b64(hmac.new(secret_key(), payload.encode(), hashlib.sha256).digest())


def issue(now: datetime | None = None) -> str:
    """A token good for `session_days()`, as `<expiry>.<signature>`."""
    now = now or datetime.now(timezone.utc)
    payload = (now + timedelta(days=session_days())).isoformat()
    return f"{payload}.{_signature(payload)}"


def verify(token: str, now: datetime | None = None) -> bool:
    """Whether a token is both genuine and still in date."""
    payload, _, signature = token.rpartition(".")
    if not payload or not hmac.compare_digest(signature, _signature(payload)):
        return False
    try:
        expiry = datetime.fromisoformat(payload)
    except ValueError:
        return False
    return expiry > (now or datetime.now(timezone.utc))


if __name__ == "__main__":  # python -m src.services.auth
    print(f"ALLOT_PASSWORD_HASH={hash_password(getpass.getpass('Password: '))}")
