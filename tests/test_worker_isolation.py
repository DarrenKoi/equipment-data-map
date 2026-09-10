"""One bad file or a rude QUIT never costs a host its good measurements.

ftplib raises ValueError outside ``all_errors`` (malformed SIZE reply,
undecodable filename, CRLF in a command), and ``FTP.__exit__`` lets an error
reply to QUIT escape. Either one used to turn a host with N-1 good sizes into
a single host-level failure.

Runs bare (`python tests/test_worker_isolation.py`) until pytest lands.
"""

import socket
import sys
from contextlib import contextmanager
from ftplib import error_temp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ftp_handler.direct_downloader import fleet_downloader as fd
from ftp_handler.direct_downloader.fleet_downloader import FtpFleetDownloader, HostSpec, local_target


class _Ftp:
    def voidcmd(self, cmd):
        return "213 20260910123456"

    def nlst(self, remote_dir):
        return ["ok.log", "bad.log", "also_ok.log"]

    def size(self, remote_path):
        if "bad" in remote_path:
            raise ValueError("invalid literal for int() with base 10: 'garbage'")
        return 7


def test_value_error_is_isolated_to_its_file():
    dl = FtpFleetDownloader(user="u", password="p", max_concurrency=1)
    dl._session = contextmanager(lambda spec: iter([_Ftp()]))
    sizes, failures = dl._size_worker(HostSpec("h", listings=[fd.ListDir("/log")]))
    assert [s.remote_path for s in sizes] == ["/log/ok.log", "/log/also_ok.log"]
    assert [f.remote_path for f in failures] == ["/log/bad.log"]


def test_error_reply_to_quit_does_not_fail_the_host():
    class _QuitHostile(fd.FTP):
        def connect(self, *a, **k):
            self.sock = socket.socket()  # a live socket, so __exit__ really sends QUIT
            return "220"
        def login(self, *a, **k): return "230"
        def set_pasv(self, v): pass
        def quit(self): raise error_temp("421 Service not available")

    fd.FTP, orig = _QuitHostile, fd.FTP
    try:
        with FtpFleetDownloader(user="u", password="p")._session(HostSpec("h")):
            pass  # exiting must not raise
    finally:
        fd.FTP = orig


def test_host_from_the_wire_cannot_traverse():
    assert local_target("/dest", "../../etc", "/x/passwd") == Path("/dest/etc/x/passwd")
    assert local_target("/dest", "10.0.0.1", "/x/a.log") == Path("/dest/10.0.0.1/x/a.log")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
