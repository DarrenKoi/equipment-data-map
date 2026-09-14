"""Is the office proxy up? Prints status codes, never the URL or token.

    python tests/check_proxy.py
        FTP_PROXY_TOKEN empty (trusted no-auth proxy)  ->  no-token 200  means ready
        FTP_PROXY_TOKEN set                            ->  no-token 401 / token 200  means ready

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
probes = [("no-token", {})]
if token:
    probes.append(("token", {"Authorization": f"Bearer {token}"}))
for label, headers in probes:
    try:
        code = requests.post(url, json={"specs": []}, headers=headers, timeout=10).status_code
    except requests.RequestException as exc:
        code = type(exc).__name__
    print(label, code)
