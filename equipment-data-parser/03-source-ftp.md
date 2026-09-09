# Letter 03: Source interface, FTP adapter, fake FTP

## Goal

A read-only `Source` interface, its FTP implementation over the vendored
`ftp_handler`, and a fake FTP server plus fixture tree that every later
letter reuses.

## Read

`spec.md` §4.1 (the interface and why it has no range read), §4.2 (the
metadata Inventory needs), §6 (read-only account, concurrency 1, path
escape), §7 (fake trees).

`ftp_handler/__init__.py` and `ftp_handler/core/client.py` — read those two
before writing any adapter code. Do not read the whole package.

## Build

- First, before any adapter code: confirm this machine's `.env` actually
  reaches the proxy. The engineer filled `FTP_PROXY_URL` and `FTP_PROXY_TOKEN`
  in an untracked `.env` at the office (template: `.env.example`); nothing has
  checked those values yet, and everything below assumes the proxy is real.
  Both routes exist in the vendored `ftp_handler/proxy/flask_proxy.py`, so
  this needs no code — two requests, from the repository root:

  ```
  curl -sS -m 5 "$FTP_PROXY_URL/healthz_sknn_v3"
  curl -sS -m 5 -o /dev/null -w '%{http_code}\n' -X POST \
    -H "Authorization: Bearer $FTP_PROXY_TOKEN" -H 'Content-Type: application/json' \
    -d '{"specs":[]}' "$FTP_PROXY_URL/list_dirs_sknn_v3"
  ```

  On Windows call `curl.exe` — PowerShell may alias `curl` to
  `Invoke-WebRequest`, whose flags differ. Read the two values from `.env`
  yourself; do not print the token, and do not put either value in
  `progress.md`.

  `{"status": "ok"}` then `200` passes: append `wip` with
  `env: proxy reachable, token accepted` and continue. The second call is not
  redundant — `healthz()` is the only route that skips the token check, so a
  `200` there with a `401` below means a wrong token that health alone would
  have passed. Either failure is `blocked` plus a `problems/03-problems.md`
  entry naming which of the two calls failed and its status code: a wrong
  `.env` is a fact about this office, and the engineer fixes it, not you.
  `{"specs":[]}` is deliberately empty so this clears the token check without
  contacting equipment — never substitute a real host to "also test FTP",
  which would be equipment access before an approved plan.

  If this machine is on the direct side (`fleet_downloader()` returns the
  direct class, or `FTP_TRANSPORT=direct`), there is nothing to reach yet;
  append `wip` with `env: direct transport, no proxy check` and continue.

- `equipment_map/source/base.py`: `Source` with exactly `listdir(path)`,
  `size(path)`, `download(path, max_bytes)`, `close()`. Entries carry name,
  is_dir, size, raw mtime string, mtime source (`LIST`/`MDTM`/`SMB`), UTC
  mtime or `None`. No write method exists, and no range read exists — spec
  §4.1 states why, and adding one would silently break the per-file byte
  budget on the proxy transport.
- `download(path, max_bytes)` never truncates. It calls `size(path)` first
  and, when the file is larger than `max_bytes`, returns no bytes and a
  skip reason `oversize` for the caller to record as a metadata-only entry.
  A stable file at or under the budget is returned whole. The shared download
  guard calls this boundary; it also enforces aggregate budgets. Every later content read uses both guards.
- `equipment_map/source/ftp.py` on `ftp_handler`, not on `ftplib`. Rules:
  - Get the downloader class from `ftp_handler.fleet_downloader()`. Never
    import `ftp_handler.direct_downloader` or `ftp_handler.proxy` directly:
    the Windows engineer PCs have no FTP egress and must go through the
    proxy, and that choice belongs to the machine, not to this module.
  - One `HostSpec` — this is a fleet of one. `listings=[ListDir(dir)]` for
    `listdir`, `files=[path]` for `download`.
  - Construct with `max_concurrency=1` and `passive=True` (spec §6 sets the
    default concurrency to 1; the library's default is 48).
  - Resolve and reject any path outside the allowed roots before building
    the spec, so a bad path never reaches the wire.
  - Never call the downloader's `upload`. The `Source` exposes no path to it.
  - `ftp_handler` is vendored and read-only. If an item here seems to need a
    change inside it, stop and append `blocked` rather than editing it.
- Before implementing `listdir`, the engineer must settle how the proxy
  transport supplies modified times. Append `waiting` naming the two
  candidates below and stop until `progress.md` holds a human line
  `03 confirmed <UTC date> | proxy-mtime: <extend-proxy | direct-only-inventory>`.

  The gap is real and blocks §4.2, not a detail: `FtpFleetDownloader.list_dirs`
  returns `HostListing(host, paths)` — **path strings only** — on both
  transports, and `size_dirs` adds size but no time. Only
  `ftp_handler.core.FtpClient.list_details` yields size, `modified`, and the
  raw `LIST` line, and that class is direct `ftplib` with no proxy twin. The
  proxy's `/list` route returns `{"host", "paths"}` and has no field to carry
  a time. Without mtime there is no oldest/newest sample (§4.4) and no
  `active_candidate`, so the data map loses its whole time story on Windows.
  - `extend-proxy`: add a detailed-listing route to `flask_proxy.py` and a
    matching client call, both carrying size, raw mtime string, and its
    source. Upstream `skewnono_v3_nuxt` change first, then re-vendor; the
    proxy host needs a redeploy.
  - `direct-only-inventory`: Windows runs listing through a host that has
    direct FTP reach and only samples through the proxy. No library change,
    but stage 3 then needs two machines and the letters that assume one
    engineer on one PC must say so.

  Do not choose for the engineer, and do not start `ftp.py`'s `listdir`
  before the `confirmed` line exists. `size`, `download`, and `close` do not
  depend on the answer — build and test those first, then append `wip`.
- Before implementing `secrets.py`, the engineer must confirm the
  company-approved keystore per platform. Append `waiting` naming the two
  candidates below and stop until `progress.md` holds a human line
  `03 confirmed <UTC date> | keystore: <win32 backend>, <darwin backend>`.
- `equipment_map/secrets.py`: `lookup(alias)` delegates to one module-level
  backend chosen by `sys.platform` at import. Candidates: `win32` → Windows
  Credential Manager (`ctypes` `CredReadW`, generic credential named
  `equipment-map/<alias>`); `darwin` → login Keychain (`security
  find-generic-password -s equipment-map -a <alias> -w` via `subprocess`);
  every other platform → `UnsupportedKeystore`, which `next` maps to exit
  20 before any connection. Both are stdlib; no portable fallback and no
  file-based store exists. `set_backend(obj)` is the test seam; tests use
  a dict-backed fake. Never read credentials from argv or environment.
  The alias resolves to the `user`/`password` passed to the downloader
  constructor; over the proxy those cross the HTTP hop, so the proxy URL
  must be HTTPS and `FTP_PROXY_TOKEN` must be set.
- `equipment_map/transport_check.py`: `check()` returns the transport name,
  why it was chosen (`platform` or `FTP_TRANSPORT`), and for `proxy` the result
  of two calls. Both routes already exist in
  `ftp_handler/proxy/flask_proxy.py`; nothing on the client side calls either,
  so this is two `requests` calls with the connect timeout from the same
  tuning, not a new library.
  - `GET <FTP_PROXY_URL>/healthz_sknn_v3` → `{"status": "ok"}`. Reachability
    only: `healthz()` is the one route that skips `_unauthorized()`, so a 200
    here proves nothing about the token.
  - `POST <FTP_PROXY_URL>/list_dirs_sknn_v3` with `{"specs": []}` → 200 means
    the token is accepted, 401 means it is not. An empty spec list reaches the
    auth check and then builds a downloader with nothing to do, so no
    equipment is contacted. Do not send a real host here to "also test FTP" —
    that is equipment access before an approved plan.

  `preflight` calls it and exits 30 with
  `NEXT: INSTALL-OR-UPGRADE` when the proxy does not answer. Direct transport
  needs no call — there is nothing to reach until a plan names equipment.
  Print the transport name and reachable/unreachable only: spec §5 keeps the
  URL, host and token off stdout, and an unreachable proxy is exactly when
  someone is tempted to echo the URL they just typed into `.env`.
  This check never contacts equipment, so it stays outside plan approval.

- `tests/fixtures/serve.py`: `python -m tests.fixtures.serve` starts the
  fake FTP (and, after letter 04, fake SMB) on ephemeral ports, prints
  `FTP_PORT=<n>` and `SMB_PORT=<n>`, and runs until Ctrl-C. Engineers use
  it in letter 16; skills never start it.
- `tests/fixtures/tree.py`: builds a directory tree in a temp dir with
  100 log files differing only by date and lot tokens, 20 CSVs, 5 JSON, 3
  XML, 2 PNG, 1 random-bytes "encrypted" file, 1 truncated zip, 1 nested
  zip, 1 file larger than the per-file byte budget, and 1 file that is
  newest by minutes. Fixed content and fixed mtimes so runs are
  reproducible.
- `tests/fixtures/fake_ftp.py`: `pyftpdlib` on an ephemeral port with a
  read-only user (`elr` permissions only).
- `tests/fixtures/fake_proxy.py`: `flask` serving `ftp_proxy_sknn_v3` in a
  thread against the fake FTP, so the proxy transport is exercised on the
  CI machine. The Windows path must not go untested until someone is
  sitting at a Windows PC.

- `equipment_map/download_guard.py`: the single entry point for every
  content transfer, including later signature reads. Check approved roots,
  allow/deny patterns, metadata-derived active candidates, per-file size,
  remaining total bytes/files, requests, and time before calling Source.
  Reserve and persist usage before transfer; resume never resets counters.
  Completed downloads are reusable by source scope, path, size and mtime.
  Uncertain reservations stay charged until reconciled; never refund bytes
  merely because a process died. Letter 06 adds header-specific limits.
- `Source.download` must also enforce the byte cap during transfer, including
  equipment-to-proxy traffic. SIZE alone cannot bound a growing file. If the
  vendored API cannot enforce it, record `blocked` for an upstream release
  and proxy redeploy; do not fake compliance with a post-download check.
  Discard partial copies and retain the metadata/failure reason.

## Done when

```
python -m pytest -q tests/test_source_ftp.py
```

That file covers: listing returns the fixture counts; `size` returns the
exact byte counts; `download` returns whole files and refuses the
over-budget fixture with reason `oversize`, having transferred none of its
bytes; a path outside the root is refused before any request; the `Source`
class exposes no method whose name contains `write`, `delete`, `rename`,
`mkdir`, `put`, or `range`; the fake server logs no STOR/DELE/RNFR/MKD
command during the test; the same assertions pass against both transports,
with `FTP_TRANSPORT=proxy` pointed at `fake_proxy`; `fleet_downloader`
returns the proxy class for `win32` and the direct class otherwise; `preflight` exits 30 without touching equipment when the proxy
health endpoint refuses the connection or answers non-200, and when the
health endpoint is fine but the empty-spec list POST returns 401,
and its stdout contains neither the URL nor the token; with the
platform forced to `win32` and `CredReadW` mocked, and with `darwin` and
`subprocess.run` mocked, `lookup` issues exactly the call above and returns
the secret without logging it; with `linux` it raises `UnsupportedKeystore`
without touching the network.

Also cover a file growing after SIZE on both transports: the transfer cap
is enforced before excess bytes are received, no partial evidence is kept,
and usage remains charged after interruption. Guard tests prove denied and
active candidates trigger zero content requests.
