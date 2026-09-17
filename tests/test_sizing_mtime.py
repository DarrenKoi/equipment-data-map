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


def test_nothing_the_probe_can_raise_escapes_it():
    # It runs inside the per-file loop after a SIZE that already succeeded, so
    # anything escaping sinks the whole host and loses every measurement on that
    # connection. Not a hypothetical: the skewnono_v3_nuxt fake returns None
    # from voidcmd, and the narrower catch this replaced let a TypeError out.
    class _Hostile:
        def voidcmd(self, cmd):
            return None

    assert _mdtm(_Hostile(), "/data/a.log") is None


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


class _ModeFtp:
    """A strict server: nlst() flips to ASCII (as ftplib's does), and SIZE is
    refused unless the session is back in binary mode."""

    def __init__(self, refuse_type_i=False):
        self.mode, self.refuse_type_i = "A", refuse_type_i

    def voidcmd(self, cmd):
        if cmd == "TYPE I":
            if self.refuse_type_i:
                raise error_perm("504 TYPE I not implemented")
            self.mode = "I"
            return "200 Type set to I"
        return "213 20260910123456"

    def nlst(self, remote_dir):
        self.mode = "A"
        return ["a.log", "b.log"]

    def size(self, remote_path):
        if self.mode != "I":
            raise error_perm("550 SIZE not allowed in ASCII mode.")
        return 7


def _size_with(fake):
    from contextlib import contextmanager
    from ftp_handler.direct_downloader.fleet_downloader import FtpFleetDownloader, HostSpec, ListDir

    dl = FtpFleetDownloader(user="u", password="p", max_concurrency=1)
    dl._session = contextmanager(lambda spec: iter([fake]))
    return dl._size_worker(HostSpec("h", listings=[ListDir("/log")]))


def test_listing_does_not_undo_binary_mode():
    # nlst() sends TYPE A itself; sizing after it must re-assert TYPE I, or a
    # strict server refuses every SIZE and the whole listing measures nothing.
    sizes, failures = _size_with(_ModeFtp())
    assert [s.remote_path for s in sizes] == ["/log/a.log", "/log/b.log"]
    assert sizes[0].size == 7 and failures == []


def test_refused_type_i_does_not_sink_the_host():
    # The refusal is per file, in the same shape as any other SIZE failure.
    sizes, failures = _size_with(_ModeFtp(refuse_type_i=True))
    assert sizes == [] and [f.remote_path for f in failures] == ["/log/a.log", "/log/b.log"]
    assert all("error_perm" in f.error for f in failures)


def test_imports_without_a_time_zone_database():
    # Windows has no system tz database and the engineer PCs carry no tzdata
    # wheel, so a ZoneInfo lookup at import time made the whole package
    # unimportable there. Empty TZPATH + no tzdata reproduces that on any OS.
    import os
    import subprocess

    code = (
        "import sys; sys.modules['tzdata'] = None; "
        "import ftp_handler.core, ftp_handler.direct_downloader, ftp_handler.proxy"
    )
    env = {**os.environ, "PYTHONTZPATH": ""}
    root = Path(__file__).resolve().parent.parent
    run = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-400:]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
