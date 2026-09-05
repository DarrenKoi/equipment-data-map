# Letter 03: Source interface, FTP adapter, fake FTP

## Goal

A read-only `Source` interface, its FTP implementation, and a fake FTP
server plus fixture tree that every later letter reuses.

## Read

`spec.md` §4.1, §6 (read-only account, concurrency 1, path escape), §7 (fake
trees).

## Build

- `equipment_map/source/base.py`: `Source` with exactly `listdir(path)`,
  `read_range(path, offset, length)`, `download(path, max_bytes)`,
  `close()`. Entries carry name, is_dir, size, raw mtime string, mtime
  source (`LIST`/`MDTM`/`SMB`), UTC mtime or `None`. No write method exists.
- `equipment_map/source/ftp.py` on `ftplib`: one connection, passive mode,
  `MDTM` when the server supports it. Reject any path that resolves outside
  the allowed roots before sending it.
- Credential lookup by alias from the OS keystore behind one function
  `equipment_map/secrets.py:lookup(alias)`; tests monkeypatch it. Never read
  credentials from argv or environment.
- `tests/fixtures/tree.py`: builds a directory tree in a temp dir with
  100 log files differing only by date and lot tokens, 20 CSVs, 5 JSON, 3
  XML, 2 PNG, 1 random-bytes "encrypted" file, 1 truncated zip, 1 nested
  zip, 1 file larger than the per-file byte budget, and 1 file that is
  newest by minutes. Fixed content and fixed mtimes so runs are
  reproducible.
- `tests/fixtures/fake_ftp.py`: `pyftpdlib` on an ephemeral port with a
  read-only user (`elr` permissions only).

## Done when

```
python -m pytest -q tests/test_source_ftp.py
```

That file covers: listing returns the fixture counts; `read_range`
returns exact bytes; `download` stops at `max_bytes` and reports truncation;
a path outside the root is refused before any request; the `Source` class
exposes no method whose name contains `write`, `delete`, `rename`, `mkdir`,
or `put`; the fake server logs no STOR/DELE/RNFR/MKD command during the
test.
