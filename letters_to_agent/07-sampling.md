# Letter 07: Sampling with budgets and dedup

## Goal

Download only representatives per family, under every download budget,
deduplicated by content, honouring allow/deny and `active_candidate`.

## Read

`spec.md` §4.4 in full, §6 (budget stops).

## Build

- `equipment_map/sampling.py`: pick oldest, newest, median-size, and up to
  two outliers per family. Deny-pattern members get metadata only. The
  newest file of a family with a single inventory is `active_candidate`:
  metadata only.
- SHA-256 of downloaded bytes; `truncated: true/false`; duplicates share
  one evidence file.
- Budgets: per-equipment file count, per-file bytes, total bytes, wall
  time. Any breach stops downloading at once and records the reason.
- Family-level checkpoint; resume skips completed families.
- Evidence lands in `rollouts/<id>/data-map/evidence/<family>/<sha>`.
- Update-period inference: from mtime gaps of existing members or a second
  inventory. Weak evidence → `unknown`.

## Done when

```
python -m pytest -q tests/test_sampling.py
```

Covers: 100-file family yields 3–5 samples; total-bytes budget stops
before the next download; deny pattern produces no evidence file; newest
file is `active_candidate` with no download; identical files produce one
evidence file; interrupted sampling resumes without re-downloading finished
families; period is `unknown` when fewer than three members exist.
