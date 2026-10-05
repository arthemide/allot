"""Masking applied to everything captured before it touches the disk.

Amounts, quantities, ISINs and fund labels are what the dumps are for, so they
stay. What goes: tokens and session identifiers, IBANs, account and membership
numbers, and personal details. Headers and cookies are never captured in the
first place, so there is nothing to mask there.

The rules lean towards masking too much: a lost timestamp costs nothing, a
leaked account number does. The dumps still get read before any of them
becomes a test fixture.

No I/O: text in, text out.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MASK = "***"

# Key fragments, normalised (lowercase, alphanumeric only), whose value is a
# secret, an identifier or a personal detail. Matched as substrings.
SENSITIVE_KEYS = (
    "token",
    "cookie",
    "authorization",
    "password",
    "secret",
    "session",
    "csrf",
    "xsrf",
    "jwt",
    "nonce",
    "iban",
    "bic",
    "email",
    "mail",
    "phone",
    "telephone",
    "mobile",
    "firstname",
    "lastname",
    "prenom",
    "holder",
    "titulaire",
    "birth",
    "naissance",
    "address",
    "adresse",
    "accountnumber",
    "accountid",
    "accountkey",
    "numerocompte",
    "contractnumber",
    "contractid",
    "contratid",
    "numero",
    "adherent",
    "adhesionid",
    "numeroadhesion",
    "customerid",
    "clientid",
    "clientnumber",
    "userid",
    "username",
    "login",
    "hash",
)
# Keys that are only sensitive when they are the whole key: as fragments they
# would fire on everything ("nom" is in "nombre", "id" in "valid").
SENSITIVE_EXACT_KEYS = ("nom", "id", "uid", "key", "code", "state")
# Query parameters get the same treatment.
SENSITIVE_PARAMS = SENSITIVE_KEYS + ("code", "state", "key", "account", "contrat")

# IBAN, written compact or in groups of four. An ISIN is 12 characters, below
# the shortest IBAN (15), so the compact form never takes one.
IBAN = re.compile(
    r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
    r"|\b[A-Z]{2}\d{2}(?: [A-Z0-9]{4}){3,7}(?: [A-Z0-9]{1,4})?\b"
)
# A long run of digits on its own: account, contract or customer numbers. The
# lookarounds keep the digits inside an ISIN out of it.
LONG_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d{9,}(?![A-Za-z0-9])")
# Hex identifiers and hashes: BoursoBank's account keys, and its 15-character
# customer hash in every API path (`/_user_/_<hash>_/`). Some ISINs are all
# hex too (BE0974293251), so a valid ISIN is spared.
HEX_ID = re.compile(r"(?<![A-Za-z0-9])(?=[a-fA-F]*\d)[a-fA-F0-9]{12,}(?![A-Za-z0-9])")
ISIN = re.compile(r"[A-Z]{2}[A-Z0-9]{9}\d")
JWT = re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]*")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# In HTML: hidden inputs (CSRF tokens) and `token: "..."` pairs in inline
# scripts or data attributes.
HIDDEN_INPUT = re.compile(r"<input\b[^>]*\btype=[\"']?hidden\b[^>]*>", re.I)
VALUE_ATTR = re.compile(r"\bvalue=(\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
META_TOKEN = re.compile(
    r"(<meta\b[^>]*\bname=[\"'][^\"']*(?:token|csrf)[^\"']*[\"'][^>]*\bcontent=)"
    r"(\"[^\"]*\"|'[^']*')",
    re.I,
)
SECRET_PAIR = re.compile(
    r"([\"']?[\w-]*(?:token|csrf|xsrf|session|secret|password|jwt|hash)[\w-]*[\"']?"
    r"\s*[:=]\s*)(\"[^\"]*\"|'[^']*')",
    re.I,
)


def _normalise(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def is_sensitive_key(key: str) -> bool:
    norm = _normalise(key)
    return norm in SENSITIVE_EXACT_KEYS or any(f in norm for f in SENSITIVE_KEYS)


def valid_isin(code: str) -> bool:
    """ISIN check digit: letters to numbers, then Luhn over the digits."""
    digits = "".join(str(int(c, 36)) for c in code[:-1]) + code[-1]
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def _hex_id(match: re.Match) -> str:
    code = match.group(0)
    return code if ISIN.fullmatch(code) and valid_isin(code) else MASK


def mask_string(text: str) -> str:
    """Mask what looks like an identifier anywhere in free text."""
    for pattern in (JWT, EMAIL, IBAN, LONG_NUMBER):
        text = pattern.sub(MASK, text)
    return HEX_ID.sub(_hex_id, text)


def mask_url(url: str) -> str:
    """Keep the shape of the endpoint, drop the identifiers and the fragment."""
    parts = urlsplit(url)
    path = "/".join(mask_string(segment) for segment in parts.path.split("/"))
    params = [
        (
            name,
            MASK
            if any(f in _normalise(name) for f in SENSITIVE_PARAMS)
            else mask_string(value),
        )
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, path, urlencode(params, safe="*"), "")
    )


def mask_json(value: Any) -> Any:
    """Mask a decoded JSON document, keeping its structure and its numbers.

    A sensitive key only loses its value when that value is a scalar: under
    `contract` there may be the balance the dump is for.
    """
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            if is_sensitive_key(key) and not isinstance(item, (dict, list)):
                item = MASK if item is not None else None
            masked[mask_string(key)] = mask_json(item)
        return masked
    if isinstance(value, list):
        return [mask_json(item) for item in value]
    if isinstance(value, str):
        return mask_string(value)
    return value


def mask_html(html: str) -> str:
    """Mask a server-rendered page: hidden fields, inline secrets, identifiers."""
    html = HIDDEN_INPUT.sub(
        lambda m: VALUE_ATTR.sub(f'value="{MASK}"', m.group(0)), html
    )
    html = META_TOKEN.sub(lambda m: f'{m.group(1)}"{MASK}"', html)
    html = SECRET_PAIR.sub(lambda m: f'{m.group(1)}"{MASK}"', html)
    return mask_string(html)
