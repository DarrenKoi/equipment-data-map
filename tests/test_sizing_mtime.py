"""The sizing pass carries a UTC mtime, on both transports.

Letters 05-07 need an mtime per file (newest/oldest samples, update-period
inference) and the fleet listing carries paths only. MDTM rides along with the
SIZE that `size_dirs` already issues, so the metadata pass answers both
questions in one connection -- and, unlike LIST parsing, RFC 3659 fixes MDTM to
GMT, so there is no server-timezone guess to get wrong.

Runs bare (`python tests/test_sizing_mtime.py`) until pytest lands.
"""

import sys
from datetime import datetime, timezone
from ftplib import error_perm
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ftp_handler.direct_downloader.fleet_downloader import FileSize, _mdtm
from ftp_handler.proxy.proxy_downloader import _parse_modified


class _FakeFtp:
    """Just enough FTP to answer one MDTM the way a server would."""

    def __init__(self, reply):
        self._reply = reply

    def voidcmd(self, cmd):
        assert cmd.startswith("MDTM ")
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply


def test_mdtm_parses_as_utc():
    got = _mdtm(_FakeFtp("213 20260910123456"), "/data/a.log")
    assert got == datetime(2026, 9, 10, 12, 34, 56, tzinfo=timezone.utc)


def test_mdtm_drops_fractional_seconds():
    got = _mdtm(_FakeFtp("213 20260910123456.789"), "/data/a.log")
    assert got == datetime(2026, 9, 10, 12, 34, 56, tzinfo=timezone.utc)


def test_mdtm_unsupported_is_none_not_a_failure():
    # An equipment server too old for MDTM must not cost us the size we did get.
    assert _mdtm(_FakeFtp(error_perm("500 Unknown command")), "/data/a.log") is None
    assert _mdtm(_FakeFtp("213 not-a-timestamp"), "/data/a.log") is None


def test_wire_round_trip_and_older_proxy():
    original = FileSize(
        host="h", remote_path="/data/a.log", size=12,
        modified=datetime(2026, 9, 10, 12, 34, 56, tzinfo=timezone.utc),
    )
    wire = {"modified": original.modified.isoformat()}
    assert _parse_modified(wire["modified"]) == original.modified
    # A proxy deployed before mtimes: key absent, or explicitly null.
    assert _parse_modified({}.get("modified")) is None
    assert _parse_modified(None) is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
