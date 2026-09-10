# Letter 07: Sampling with budgets and dedup

## Goal

Download only representatives per family, under every download budget,
deduplicated by content, honouring allow/deny and `active_candidate`.

## Read

`spec.md` §4.4 in full, §6 (budget stops).

## Build

- `equipment_map/sampling.py`: pick oldest, newest, median-size, and up to
  two outliers per family. Deny-pattern members get metadata only.
  Reuse the metadata-derived `active_candidate` classification and shared
  guard from letters 03/06: newest, real-time and actively changing members
  stay metadata-only while stability is unproven. Signature splitting never
  clears this flag. Never download such members; record the reason.
- SHA-256 of downloaded bytes; duplicates share one evidence file. Every
  sample is a whole file — nothing is truncated (spec §4.1). Large or unknown-
  size eligible files may be downloaded; record actual bytes and per-file
  advisory overruns. Only failed/skipped transfers remain metadata-only.
- Enforce file-count and start-time gates. Total bytes are a best-effort target:
  after a completed download reaches it, stop new downloads and record the
  reason. Do not abort or discard a successful file for exceeding an estimate.
- Family-level checkpoint keyed by collection scope and family input hash;
  resume skips only matching completed families. Reuse eligible signature
  downloads without retransferring them; usage includes all content reads.
- Evidence lands in `rollouts/<id>/data-map/evidence/<family>/<sha>`.
- Update-period inference: from mtime gaps of existing members or the
  second pass. Weak evidence → `unknown`.
- `tests/test_budgets.py`: parametrized over every key in
  `rollout.json.budgets` that letters 05–07 enforce (entries, depth,
  wall time, header files per family, header requests,
  download files, per-file bytes, total bytes): assert the matching boundary
  behavior in implementation-reference.md §2. Per-file sizes are advisory;
  exhausted header limits leave signature unknown and permit eligible sampling;
  aggregate exhaustion ends content collection. No prohibited transfer occurs.
  Rate limits are tested as pacing, not as cumulative request exhaustion.

## Done when

```
python -m pytest -q tests/test_sampling.py tests/test_budgets.py
```

Covers: the fixture with enough distinct eligible representatives yields 3–5
samples; a small, protected or duplicate family may yield fewer, with reasons; total-bytes budget stops
before the next download; the large eligible fixture produces whole evidence
and an actual-byte/overrun record, and no evidence file is a partial copy; deny pattern
produces no evidence file; newest
file is `active_candidate` with no download; a file that changed between
two passes is `active_candidate` even when it is not the newest; identical files produce one
evidence file; interrupted sampling resumes without re-downloading finished
families; period is `unknown` when fewer than three members exist.

Also cover header+sample cumulative budgets across restart, signature-file
reuse without another transfer, and changed scope/input invalidating completed
family checkpoints. A protected newest file stays protected after pass 2.
