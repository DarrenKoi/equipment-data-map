# Letter 04: SMB adapter, fake SMB

## Goal

The same `Source` contract over SMB, proven by the same tests, plus
symlink and reparse point refusal.

## Read

`spec.md` §4.1, §6 (symlink/reparse), §7 (fake SMB on a non-standard port).

## Build

- `equipment_map/source/smb.py` on `smbprotocol`: read-only open flags
  only, mtime source `SMB`. Refuse to follow entries with reparse or
  symlink attributes and record them as `skipped: reparse-point`.
- `tests/fixtures/fake_smb.py`: `impacket` `smbserver` on a non-standard
  port sharing the fixture tree, started per test session.
- Parametrize `tests/test_source_ftp.py` over both adapters and rename it
  `tests/test_source.py`; add the reparse-point case for SMB.

## Done when

```
python -m pytest -q tests/test_source.py
```

Every case passes for both adapters, and the two adapters produce
identical entry lists (same names, sizes, UTC mtimes) for the fixture tree.
