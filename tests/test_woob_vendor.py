"""The vendored boursorama module loads with the woob version uv.lock pins.

The rest of the suite stubs woob out. This test runs the real thing, without
logging in, so a module refresh that needs a newer woob core fails here rather
than on the first sync. Skipped when the woob group is not installed.
"""

from __future__ import annotations

import pytest

from src.connectors.woob_bourso import MODULE, MODULES_PATH

pytest.importorskip("woob")


def test_the_vendored_module_builds_a_backend(tmp_path):
    from woob.core import WoobBase
    from woob.tools.storage import StandardStorage

    storage = StandardStorage(str(tmp_path / "state.yml"))
    woob = WoobBase(modules_path=str(MODULES_PATH), storage=storage)
    backend = woob.build_backend(
        MODULE,
        params={"login": "12345678", "password": "secret", "request_information": True},
        storage=storage,
        name="load-test",
    )
    try:
        assert type(backend).__name__ == "BoursoramaModule"
        assert type(backend.browser).__name__ == "BoursoramaBrowser"
    finally:
        backend.deinit()
