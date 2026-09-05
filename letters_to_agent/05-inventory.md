# Letter 05: Inventory with checkpoints and budgets

## Goal

Walk the allowed roots through a `Source`, store metadata only, stop on
budgets, resume from the last completed directory.

## Read

`spec.md` §4.2, §4.4 budget list, §6 (rate limits, no retry storms).

## Build

- `equipment_map/inventory.py` writing `rollouts/<id>/work/inventory.sqlite`
  with the §4.2 columns plus `visited_at`, `status`, `error_kind`.
- Directory-level checkpoint table: a directory is `done` only after all its
  entries are stored. Resume skips `done` directories.
- Budgets enforced here: max entries, max depth, requests per second,
  connections (always 1). Exceeding any budget stops the walk immediately
  with reason recorded; it is not an error.
- Connection failure: record the diagnostic, stop, no retries beyond one
  reconnect.
- Denied real-time candidate paths are listed but flagged `realtime_candidate`.

## Done when

```
python -m pytest -q tests/test_inventory.py
```

Covers, over the fake FTP: full walk counts match the fixture; max-entries
budget stops at the limit and records the reason; a walk killed mid-way
(simulate by raising after N entries) resumes and finishes with the same
row set as an uninterrupted walk; every stored mtime is UTC ISO-8601 or
`None` with the raw string kept; a dropped connection yields one reconnect
then stop.
