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
  entries are stored. Key by collection scope + pass_id + directory. Resume
  skips `done` directories only in that same scope and pass.
- Every row carries `pass_id`. Stage 1 walks once. Stage 3 walks twice:
  pass 1 full, pass 2 listing only, both charged to the same listing,
  request, and wall-time budgets. A path whose size or mtime differs
  between passes is `actively_changing`. If any budget is spent before
  pass 2 completes, pass 2 stops there with `reason: budget:<key>`,
  unlisted paths keep `pass_id` 1 only, and sampling treats their newest
  and real-time candidates as metadata-only with period `unknown`. Stage 5
  performs no inventory.
- Budgets enforced here: max entries, max depth, requests per second,
  connections (always 1). Rate limits pace requests; exceeding a count/time budget stops the walk immediately
  with reason recorded; it is not an error.
- Connection failure: record the diagnostic, stop, no retries beyond one
  reconnect.
- Denied real-time candidate paths are listed but flagged `realtime_candidate`.

## Done when

```
python -m pytest -q tests/test_inventory.py
```

Covers, over the fake FTP: full walk counts match the fixture; entry/depth/time
limits stop with `reason: budget:<key>` and no further request. With a frozen
monotonic clock, request start times obey the rate, and a required wait beyond
the deadline stops without another request. Read implementation-reference.md
§2 for counter units and §5 for unknown timestamps and deterministic order; a file rewritten between two passes is `actively_changing`; a walk killed mid-way
(simulate by raising after N entries) resumes and finishes with the same
row set as an uninterrupted walk; every stored mtime is UTC ISO-8601 or
`None` with the raw string kept; a dropped connection yields one reconnect
then stop.

A completed fake-tree directory with the same path as a real-tree directory
must not suppress the stage 3 walk; pass 1 completion must not skip pass 2.
Reconfiguration creates a fresh scope; a process restart preserves it.
