# Letter 07: Sampling with budgets and dedup

## Goal

Download only representatives per family, under every download budget,
deduplicated by content, honouring allow/deny and `active_candidate`.

## Read

`spec.md` §4.4 in full, §6 (budget stops).

## Build

- `equipment_map/sampling.py`: pick oldest, newest, median-size, and up to
  two outliers per family. Deny-pattern members get metadata only.
  `active_candidate` = the newest file of a family after a single pass, or
  any member flagged `actively_changing` across passes (letter 05): metadata
  only, never downloaded, reason recorded.
- SHA-256 of downloaded bytes; duplicates share one evidence file. Every
  sample is a whole file — nothing is truncated (spec §4.1) — so a member
  over the per-file byte budget is skipped with reason `oversize` and
  recorded as metadata only, beside the deny-pattern members.
- Budgets: per-equipment file count, per-file bytes, total bytes, wall
  time. Any breach stops downloading at once and records the reason.
- Family-level checkpoint; resume skips completed families.
- Evidence lands in `rollouts/<id>/data-map/evidence/<family>/<sha>`.
- Update-period inference: from mtime gaps of existing members or the
  second pass. Weak evidence → `unknown`.
- `tests/test_budgets.py`: parametrized over every key in
  `rollout.json.budgets` that letters 05–07 enforce (entries, depth,
  requests per second, wall time, header files per family, header requests,
  download files, per-file bytes, total bytes): the limit one above need
  completes; one below stops at once with `reason: budget:<key>` and the
  audit count of requests after the stop is zero.

## Done when

```
python -m pytest -q tests/test_sampling.py tests/test_budgets.py
```

Covers: 100-file family yields 3–5 samples; total-bytes budget stops
before the next download; the over-budget fixture file produces no
evidence file and a metadata-only row with reason `oversize`, and no
evidence file anywhere is a partial copy of its source; deny pattern
produces no evidence file; newest
file is `active_candidate` with no download; a file that changed between
two passes is `active_candidate` even when it is not the newest; identical files produce one
evidence file; interrupted sampling resumes without re-downloading finished
families; period is `unknown` when fewer than three members exist.
