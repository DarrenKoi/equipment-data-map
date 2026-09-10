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

- Read implementation-reference.md §4 and engineer-guide.md §2 first.
  Build the bounded, empty-target transport check described below using fake
  HTTP responses. The engineer verifies the actual office proxy in their own
  terminal with that check once it exists. Do not read `.env` into your context
  or put its token in a curl argument. Python import loads `.env` into that
  process only; it does not export variables to the parent shell.
  Direct transport has no proxy connectivity prerequisite.

- `equipment_map/source/base.py`: `Source` with exactly `listdir(path)`,
  `size(path)`, `download(path)`, `close()`. Entries carry name,
  is_dir, size, raw mtime string, mtime source (`LIST`/`MDTM`/`SMB`), UTC
  mtime or `None`. No write method exists, and no range read exists — spec
  §4.1 uses the library's normal whole-file download without a transfer cap.
- `download(path)` uses the vendor's normal whole-file download. Size is an
  estimate for accounting, not a cap: unknown-size and large eligible files
  may be downloaded. Do not add a capped downloader, range-read workaround or
  post-download truncation. Retain successful whole files and actual byte
  counts; record failures without claiming partial bytes as a complete sample.
  The shared guard controls approved candidates and whether another transfer
  may start; it cannot impose a hard byte ceiling on an in-flight transfer.
- `equipment_map/source/ftp.py` on `ftp_handler`, not on `ftplib`. Rules:
  - Get the downloader class from `ftp_handler.fleet_downloader()`. Never
    choose the downloader class by importing a transport directly. Shared
    `HostSpec`/`ListDir` imports follow implementation-reference.md §4:
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
- The current vendor fleet listing carries paths, not modified times. Its
  missing metadata remains a separate upstream prerequisite. Lack of an
  in-flight file-size cap is accepted and must not block downloads or require
  an upstream change or workaround. Build the Source
  contract and fake tests, then record `blocked` for the upstream release and
  deployed proxy proof in implementation-reference.md §4. A human confirmation
  alone does not supply missing code. No direct `FtpClient` bypass and no
  two-machine inventory workaround: those would change the one-PC contract.
  Do not mark letter 03 done until both transports pass the required cases.
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
  constructor. The proxy URL must use `http://` on the private company network;
  `FTP_PROXY_TOKEN` must be set. HTTP is the required internal transport for
  both office deployments and local fixtures; do not require TLS or upgrade
  the URL to HTTPS.
- `equipment_map/transport_check.py`: `check()` returns the transport name,
  why it was chosen (`platform` or `FTP_TRANSPORT`), and for `proxy` the result
  of three calls. Both routes already exist in
  `ftp_handler/proxy/flask_proxy.py`; nothing on the client side calls either,
  so this is three bounded `requests` calls with the connect timeout from the same
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
  A correct-token 200 alone does not prove auth enforcement: first send the
  same empty-spec request without a token and require 401, then require 200
  with the configured nonempty token. Validate the configured internal `http://`
  URL and refuse redirects. Apply the same HTTP policy to office deployments
  and local fixtures (see §4 of the reference).
  Print the transport name and reachable/unreachable only: spec §5 keeps the
  URL, host and token off stdout, and an unreachable proxy is exactly when
  someone is tempted to echo the URL they just typed into `.env`.
  This check never contacts equipment, so it stays outside plan approval.

- `tests/fixtures/serve.py`: `python -m tests.fixtures.serve` starts the
  fake FTP, local fake proxy (and, after letter 04, fake SMB) on ephemeral ports, prints
  `FTP_PORT=<n>`, `PROXY_PORT=<n>` and `SMB_PORT=<n>`, and runs until Ctrl-C. Engineers use
  it in letter 16; skills never start it.
- `tests/fixtures/tree.py`: builds a directory tree in a temp dir with
  100 log files differing only by date and lot tokens, 20 CSVs, 5 JSON, 3
  XML, 2 PNG, 1 fixed-seed unknown binary and 1 known encrypted archive fixture, 1 truncated zip, 1 nested
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
  allow/deny patterns, metadata-derived active candidates, remaining total
  target bytes/files, requests, and time before calling Source. Per-file size
  is advisory, never a rejection condition. Persist the transfer attempt and
  size estimate before transfer; update actual bytes afterward. Resume never
  resets counters. Total target exhaustion stops the next transfer, not the
  file already downloading.
  Completed downloads are reusable by source scope, path, size and mtime.
  An interrupted transfer with unknown actual usage becomes `usage-unknown`;
  the engineer reconciles it before another transfer. Never refund usage merely
  because a process died. Letter 06 adds header-specific limits.
- Byte accounting is best-effort on both direct and proxy transports, including
  equipment-to-proxy traffic. A growing file may exceed the estimate: keep a
  successful whole download, record the overrun and stop later transfers when
  the total target is reached. Do not claim strict network-byte enforcement.

## Done when

```
python -m pytest -q tests/test_source_ftp.py
```

That file covers: listing returns the fixture counts; `size` returns the
exact byte counts when available; `download` attempts large and unknown-size
eligible fixtures and returns whole files with actual byte counts; a path outside the root is refused before any request; the `Source`
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

Also cover a file growing after SIZE on both transports: complete successful
downloads are retained, actual bytes and overruns are recorded, and no next
transfer starts after the total target is reached. Interrupted unknown usage
is not reset on resume; partial data is not complete evidence. Guard tests prove denied and
active candidates trigger zero content requests.
