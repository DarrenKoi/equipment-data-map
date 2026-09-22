"""An empty FTP_PROXY_TOKEN means no auth on the proxy server, matching the client.

    uv run --python 3.11 --with flask --with requests python tests/test_proxy_token.py

A blank ``FTP_PROXY_TOKEN=`` line in ``.env`` lands as ``""`` in the environment;
the client already drops that (``PROXY_TOKEN = ... or None``), and the server
must not answer 401 to the header-less requests that client then sends.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask  # noqa: E402

from ftp_handler.proxy.flask_proxy import _unauthorized  # noqa: E402

app = Flask(__name__)


def check(token, header, expect_401):
    if token is None:
        os.environ.pop("FTP_PROXY_TOKEN", None)
    else:
        os.environ["FTP_PROXY_TOKEN"] = token
    headers = {"Authorization": header} if header else {}
    with app.test_request_context("/", headers=headers):
        result = _unauthorized()
    got_401 = result is not None and result[1] == 401
    assert got_401 == expect_401, (token, header, result)


check(None, None, expect_401=False)          # unset: no auth
check("", None, expect_401=False)            # blank .env line: no auth
check("", "Bearer ", expect_401=False)       # stray empty bearer is harmless
check("secret", None, expect_401=True)       # configured: header required
check("secret", "Bearer wrong", expect_401=True)
check("secret", "Bearer secret", expect_401=False)
print("ok: empty FTP_PROXY_TOKEN disables auth; a real token still enforces it")
