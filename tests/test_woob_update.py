"""The checks scripts/woob_update.py runs before it touches vendor/."""

from __future__ import annotations

import io
import tarfile

import pytest

from scripts import woob_update
from scripts.woob_update import UpdateError

INDEX = """\
[DEFAULT]
name = main
update = 202609090803
signed = 1
key_update = 202103171007

[boursorama]
version = 202608310842
dependencies =
woob_spec = ~=3.5
"""


class TestSelect:
    def test_a_compatible_entry_is_selected(self):
        assert woob_update.select(INDEX, "3.7") == {
            "version": "202608310842",
            "woob_spec": "~=3.5",
        }

    def test_an_unsigned_repository_is_refused(self):
        with pytest.raises(UpdateError, match="signed"):
            woob_update.select(INDEX.replace("signed = 1", "signed = 0"), "3.7")

    def test_a_keyring_rotation_needs_a_human(self):
        rotated = INDEX.replace("202103171007", "202701010000")
        with pytest.raises(UpdateError, match="rotated"):
            woob_update.select(rotated, "3.7")

    def test_a_module_needing_another_one_is_refused(self):
        with pytest.raises(UpdateError, match="depends"):
            woob_update.select(
                INDEX.replace("dependencies =", "dependencies = cmso"), "3.7"
            )

    def test_a_module_for_another_woob_is_refused(self):
        with pytest.raises(UpdateError, match="requires woob"):
            woob_update.select(INDEX.replace("~=3.5", ">=4.0"), "3.7")

    def test_a_missing_module_is_refused(self):
        with pytest.raises(UpdateError, match="no longer lists"):
            woob_update.select(INDEX.replace("[boursorama]", "[other]"), "3.7")


def _archive(*members: tarfile.TarInfo) -> tarfile.TarFile:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for member in members:
            tar.addfile(member, io.BytesIO(b"") if member.isfile() else None)
    buffer.seek(0)
    return tarfile.open(fileobj=buffer, mode="r:gz")


def _file(name: str) -> tarfile.TarInfo:
    return tarfile.TarInfo(name)


def _link(name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE
    info.linkname = "/etc/passwd"
    return info


class TestCheckMembers:
    def test_files_under_the_module_folder_pass(self):
        woob_update.check_members(
            _archive(_file("boursorama/__init__.py"), _file("boursorama/pages.py"))
        )

    @pytest.mark.parametrize(
        "name", ["other/__init__.py", "boursorama/../evil.py", "/boursorama/x.py"]
    )
    def test_a_path_outside_the_module_is_refused(self, name):
        with pytest.raises(UpdateError, match="path"):
            woob_update.check_members(_archive(_file(name)))

    def test_a_link_is_refused(self):
        with pytest.raises(UpdateError, match="entry type"):
            woob_update.check_members(_archive(_link("boursorama/passwd")))


def test_the_lock_pins_a_woob_version():
    assert woob_update.woob_version() == "3.7"
