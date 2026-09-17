"""spike.py runs end to end over the proxy transport against a fake FTP tree.

Home check only: passing here says the script runs, not that it passes.
The pass verdict is the office run (letter 00, Done when). Needs pyftpdlib,
flask and requests, so run it as::

    uv run --python 3.11 --with pyftpdlib --with flask --with requests \
        python tests/test_spike_fake.py
"""

import json
import contextlib
import io
import os
import socket
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_ftp(tree, port, commands):
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer

    auth = DummyAuthorizer()
    auth.add_user("ro", "ro-secret", str(tree), perm="elr")  # read-only
    class Handler(FTPHandler):
        def ftp_RETR(self, path):
            commands.append(("RETR", Path(path).relative_to(tree).as_posix()))
            return super().ftp_RETR(path)

        def ftp_SIZE(self, path):
            commands.append(("SIZE", Path(path).relative_to(tree).as_posix()))
            return super().ftp_SIZE(path)

    Handler.authorizer = auth
    server = FTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def start_proxy(port):
    from ftp_handler.proxy.flask_proxy import create_app
    from werkzeug.serving import make_server

    app = create_app()
    server = make_server("127.0.0.1", port, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def start_llm(port):
    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert self.path == "/v1/chat/completions"
            assert self.headers["Authorization"] == "Bearer llm-secret"
            reply = {"model": "glm-fake", "choices": [{"message": {
                "content": f"### Observed\n{len(body['messages'][1]['content'])} chars"}}]}
            data = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        log_message = lambda *a: None

    threading.Thread(target=HTTPServer(("127.0.0.1", port), H).serve_forever, daemon=True).start()


def main(transport="proxy"):
    tmp = Path(tempfile.mkdtemp()).resolve()
    tree, out = tmp / "ftp", tmp / "out"
    for rel, data in {
        "log/a.log": b"line1\nline2\n", "log/b.log": b"newer\n", "log/tool.bak": b"deny me",
        "log/sub/c.csv": "가,나\n".encode("cp949"), "log/sub/deep/img.png": b"\x80\xff" * 100,
        "data/note.txt": b"data", "log/sub/deep/z-big.bin": b"x" * 5000,
        "log/sub/deep/zz-next.csv": b"over budget", "secret/leak.txt": b"outside roots",
    }.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_bytes(data)
    os.utime(tree / "log/b.log", (2_000_000_000, 2_000_000_000))  # newest .log

    ftp_port, proxy_port, llm_port = free_port(), free_port(), free_port()
    # Proxy facts belong to the environment, exactly as .env would set them.
    os.environ.update(FTP_TRANSPORT=transport, FTP_PROXY_URL=f"http://127.0.0.1:{proxy_port}",
                      FTP_PROXY_TOKEN="proxy-secret")
    commands = []
    start_ftp(tree, ftp_port, commands)
    if transport == "proxy":
        start_proxy(proxy_port)
    start_llm(llm_port)

    cfg = tmp / "equipment.toml"
    cfg.write_text(f'''
[equipment]
name = "fake"
host = "127.0.0.1"
port = {ftp_port}
user = "ro"
password = "ro-secret"
roots = ["/log", "/data"]
deny = ["*.bak"]
[budget]
max_download_bytes = 1000
max_dirs = 10
sample_bytes = 8
[llm]
url = "http://127.0.0.1:{llm_port}"
model = "HCP-Medium-Latest"
api_key = "llm-secret"
timeout_s = 5
[output]
dir = "{out.as_posix()}"
''', encoding="utf-8")

    import spike

    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        assert spike.main(cfg) == 0
    stats = json.loads(stdout.getvalue())
    run_dir = Path(stats["output_dir"])
    assert (run_dir / "index.md").is_file()
    md = {p.read_text().splitlines()[0]: p.read_text() for p in run_dir.rglob("index.md")
          if "## Evidence" in p.read_text()}
    assert set(md) == {"# /log", "# /log/sub", "# /log/sub/deep", "# /data"}, set(md)
    folders = {p.parent.relative_to(run_dir).as_posix() for p in run_dir.rglob("index.md")}
    assert folders == {".", "log", "log/sub", "log/sub/deep", "data"}, folders
    assert "[sub](sub/index.md)" in md["# /log"] and "[deep](deep/index.md)" in md["# /log/sub"]
    assert "tool.bak" not in md["# /log"] and "leak.txt" not in "".join(md.values())
    assert "| b.log | .log | 6 |" in md["# /log"] and "text head" in md["# /log"]
    assert any(row.startswith("| a.log | .log | 12 |") and row.endswith("| - |")  # not sampled
               for row in md["# /log"].splitlines())
    assert "meta only" in md["# /log/sub/deep"]  # binary png
    assert "over budget" in md["# /log/sub/deep"]
    assert "glm-fake" in md["# /log"]
    assert "ro-secret" not in "".join(md.values()) and "llm-secret" not in "".join(md.values())
    assert stats["bytes"] == 5216 and stats["overrun_bytes"] == 4216, stats
    assert stats["llm_calls"] == stats["llm_success"] == 4 and stats["llm_failed"] == 0
    assert not any(path in ("log/tool.bak", "secret/leak.txt") for _, path in commands)
    assert ("RETR", "log/sub/deep/z-big.bin") in commands
    assert ("RETR", "log/sub/deep/zz-next.csv") not in commands
    print(f"ok test_spike_fake ({transport})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "proxy")
