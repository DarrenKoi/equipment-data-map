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
- Every row carries `pass_id`. Stage 1 walks once. Stage 3 walks twice:
  pass 1 full, pass 2 listing only, both charged to the same listing,
  request, and wall-time budgets. A path whose size or mtime differs
  between passes is `actively_changing`. If any budget is spent before
  pass 2 completes, pass 2 stops there with `reason: budget:<key>`,
  unlisted paths keep `pass_id` 1 only, and sampling treats their newest
  and real-time candidates as metadata-only with period `unknown`. Stage 5
  performs no inventory.
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

Covers, over the fake FTP: full walk counts match the fixture; for each
of max entries, max depth, requests per second, and wall time, a limit one
above the fixture's need completes and a limit one below stops with
`reason: budget:<key>` and no further request (wall time via the frozen
clock); a file rewritten between two passes is `actively_changing`; a walk killed mid-way
(simulate by raising after N entries) resumes and finishes with the same
row set as an uninterrupted walk; every stored mtime is UTC ISO-8601 or
`None` with the raw string kept; a dropped connection yields one reconnect
then stop.
