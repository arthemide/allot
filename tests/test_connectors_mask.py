"""Masking captured responses: identifiers go, figures stay."""

from __future__ import annotations

from src.connectors.banks import BANKS
from src.connectors.mask import MASK, mask_html, mask_json, mask_string, mask_url

IBAN = "FR7630004000031234567890143"
ISIN = "FR0010315770"


class TestMaskString:
    def test_an_iban_is_masked_compact_or_grouped(self):
        assert mask_string(f"iban {IBAN}") == f"iban {MASK}"
        assert mask_string("FR76 3000 4000 0312 3456 7890 143") == MASK

    def test_an_isin_survives_even_followed_by_text(self):
        assert mask_string(f"{ISIN} ABC") == f"{ISIN} ABC"
        assert mask_string("IE00B4L5Y983") == "IE00B4L5Y983"

    def test_long_numbers_hashes_tokens_and_emails_are_masked(self):
        text = (
            "compte 00012345678 key 9f86d081884c7d659a2feaa0c55ad015 "
            "jwt eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl mail jane.doe@example.com"
        )
        assert mask_string(text) == f"compte {MASK} key {MASK} jwt {MASK} mail {MASK}"

    def test_an_all_hex_isin_survives_a_short_hash_does_not(self):
        # Given BoursoBank's 15-character customer hash, and a Belgian ISIN
        text = "/_user_/_23502e67dfe87f9_/ BE0974293251"
        # Then only the hash goes
        assert mask_string(text) == f"/_user_/_{MASK}_/ BE0974293251"

    def test_amounts_and_dates_are_kept(self):
        text = "1 234,56 EUR le 2026-10-05, 12.5 parts"
        assert mask_string(text) == text


class TestMaskUrl:
    def test_identifiers_in_the_path_and_secrets_in_the_query_go(self):
        url = (
            "https://clients.boursobank.com/compte/pea/"
            "9f86d081884c7d659a2feaa0c55ad015/positions"
            "?token=abc&accountId=42&page=2#frag"
        )
        assert mask_url(url) == (
            f"https://clients.boursobank.com/compte/pea/{MASK}/positions"
            f"?token={MASK}&accountId={MASK}&page=2"
        )

    def test_a_plain_url_is_unchanged(self):
        url = "https://adherent.gie-afer.fr/api/supports?type=uc"
        assert mask_url(url) == url


class TestMaskJson:
    def test_sensitive_scalars_go_and_figures_stay(self):
        # Given a payload mixing holder details with a position
        payload = {
            "accountNumber": "00012345678",
            "holder": {"firstName": "Jane", "lastName": "Doe"},
            "iban": IBAN,
            "id": 17,
            "csrfToken": "abc",
            "USER_HASH": "abc",
            "positions": [
                {"isin": ISIN, "label": "LYXOR MSCI WORLD", "quantity": 3.5},
                {"isin": "IE00B4L5Y983", "amount": 1234.56, "nombre": 2},
            ],
            "contract": {"balance": 10000.0},
            "note": f"versement depuis {IBAN}",
            "empty": None,
        }
        # When it is masked
        masked = mask_json(payload)
        # Then every identifier is gone, and every figure and ISIN is there
        assert masked["accountNumber"] == MASK
        assert masked["holder"] == {"firstName": MASK, "lastName": MASK}
        assert masked["iban"] == MASK
        assert masked["id"] == MASK
        assert masked["csrfToken"] == MASK
        assert masked["USER_HASH"] == MASK
        assert masked["positions"] == payload["positions"]
        assert masked["contract"] == {"balance": 10000.0}
        assert masked["note"] == f"versement depuis {MASK}"
        assert masked["empty"] is None

    def test_a_sensitive_key_holding_null_stays_null(self):
        assert mask_json({"token": None}) == {"token": None}

    def test_an_identifier_used_as_a_key_is_masked(self):
        assert mask_json({"00012345678": {"balance": 1.0}}) == {MASK: {"balance": 1.0}}


class TestMaskHtml:
    def test_hidden_fields_meta_tokens_and_inline_secrets_go(self):
        html = (
            '<meta name="csrf-token" content="s3cr3t">'
            '<input type="hidden" name="_token" value="s3cr3t">'
            '<input type="text" value="visible">'
            '<script>var cfg = {"sessionId": "s3cr3t", apiToken: \'s3cr3t\','
            ' "USER_HASH": "s3cr3t"};</script>'
            f"<td>{ISIN}</td><td>1 234,56 €</td>"
        )
        masked = mask_html(html)
        assert "s3cr3t" not in masked
        assert 'value="visible"' in masked
        assert f"<td>{ISIN}</td><td>1 234,56 €</td>" in masked


class TestBanks:
    def test_only_the_bank_domains_and_their_subdomains_are_allowed(self):
        bourso = BANKS["bourso"]
        assert bourso.allows("https://clients.boursobank.com/x")
        assert bourso.allows("https://boursorama.com/")
        assert bourso.allows("data:image/png;base64,AAAA")
        assert not bourso.allows("https://www.google-analytics.com/collect")
        assert not bourso.allows("https://evilboursobank.com/")
        assert not BANKS["afer"].allows("https://clients.boursobank.com/")
