"""Is the office proxy up and enforcing its token? Prints two status codes, never the URL or token.

    python tests/check_proxy.py     ->  no-token 401 / token 200  means ready

An empty spec list reaches the auth check and then does nothing, so no
equipment is contacted.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests

import ftp_handler  # noqa: F401 - folds .env into the environment

url = os.environ["FTP_PROXY_URL"].rstrip("/") + "/list_dirs_sknn_v3"
token = os.environ.get("FTP_PROXY_TOKEN", "")
for label, headers in (("no-token", {}), ("token", {"Authorization": f"Bearer {token}"})):
    try:
        code = requests.post(url, json={"specs": []}, headers=headers, timeout=10).status_code
    except requests.RequestException as exc:
        code = type(exc).__name__
    print(label, code)
