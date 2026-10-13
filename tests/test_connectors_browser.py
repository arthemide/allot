"""Safe metadata captured while discovering a bank's browser flow."""

import pytest

# Playwright lives in the optional `connectors` group.
pytest.importorskip("playwright")

from src.connectors.browser import Recorder  # noqa: E402


def test_json_shape_keeps_structure_without_string_values():
    shape = Recorder._shape(
        {
            "qrcode": "secret-qr-payload",
            "nested": ["another-secret", 42, True, "ignored"],
        }
    )

    assert shape == {
        "qrcode": {"type": "string", "length": 17, "base64_bytes": None},
        "nested": [
            {"type": "string", "length": 14, "base64_bytes": None},
            "int",
            "bool",
        ],
    }
