"""The one branch worth pinning: which transport a machine gets.

``requests`` is stubbed because the proxy client imports it at module level and
a dev box has no reason to have it installed. Runs under pytest, or bare:
``python tests/test_ftp_transport.py``.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.modules.setdefault("requests", MagicMock())

from ftp_handler import fleet_downloader
from ftp_handler.direct_downloader import FtpFleetDownloader as Direct
from ftp_handler.proxy import FtpFleetDownloader as Proxy

os.environ.pop("FTP_TRANSPORT", None)  # a real one would mask the platform tests


def test_windows_gets_the_proxy():
    assert fleet_downloader("win32") is Proxy
    assert fleet_downloader("linux") is Direct
    assert fleet_downloader("darwin") is Direct


def test_env_overrides_the_platform():
    os.environ["FTP_TRANSPORT"] = "direct"
    try:
        assert fleet_downloader("win32") is Direct
    finally:
        del os.environ["FTP_TRANSPORT"]


def test_bad_transport_is_loud():
    os.environ["FTP_TRANSPORT"] = "sftp"
    try:
        fleet_downloader("linux")
    except ValueError as exc:
        assert "sftp" in str(exc)
    else:
        raise AssertionError("a typo'd FTP_TRANSPORT must not fall through")
    finally:
        del os.environ["FTP_TRANSPORT"]


def test_both_transports_are_drop_in():
    public = lambda cls: {n for n in dir(cls) if not n.startswith("_")}
    assert public(Proxy) == public(Direct)


def test_dotenv_fills_only_missing_keys():
    from ftp_handler import load_dotenv

    env_file = Path(__file__).resolve().parent / "_tmp.env"
    env_file.write_text(
        '# comment\nFTP_PROXY_URL="http://from-dotenv:9000"\nFTP_TRANSPORT=proxy\n\n',
        encoding="utf-8",
    )
    os.environ["FTP_TRANSPORT"] = "direct"  # a real env var must survive
    os.environ.pop("FTP_PROXY_URL", None)
    try:
        load_dotenv(env_file)
        assert os.environ["FTP_PROXY_URL"] == "http://from-dotenv:9000"
        assert os.environ["FTP_TRANSPORT"] == "direct"
    finally:
        env_file.unlink()
        os.environ.pop("FTP_PROXY_URL", None)
        os.environ.pop("FTP_TRANSPORT", None)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
