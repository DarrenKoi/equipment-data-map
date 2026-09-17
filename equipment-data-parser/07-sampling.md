# Letter 07: Sampling with budgets and dedup

## Goal

Download only representatives per family, under every download budget,
deduplicated by content, honouring allow/deny and `active_candidate`.

## Read

`spec.md` §4.4 in full, §4.7 (on-disk names), §6 (budget stops).

## Build

Use implementation-reference.md §5 for eligibility, hash rank and ties.

- `equipment_map/sampling.py`: per family, pick from the eligible members
  only — never denied, never `active_candidate` (letter 06 flags):
  - `pattern`: the three latest by `mtime_utc`, then two more by hash rank
    from the remaining eligible members. The latest three show the current
    format; the two ranked picks spread the view over older files.
  - `loose`: up to three by hash rank.
  Hash rank is the deterministic stand-in for random choice, so a resume or
  a rerun over the same inventory picks the same files. Five and three are
  ceilings: fewer eligible members give fewer samples, with reasons.
  Record the skip reason for every protected member; never download one.
- Every transfer goes through letter 03's download guard. SHA-256 of the
  downloaded bytes; duplicates share one evidence file and no replacement is
  downloaded. Every sample is a whole file — nothing is truncated
  (spec §4.1). Large or unknown-size eligible files may be downloaded; record
  actual bytes and per-file advisory overruns. Only failed/skipped transfers
  remain metadata-only.
- Enforce file-count and start-time gates. Total bytes are a best-effort target:
  after a completed download reaches it, stop new downloads and record the
  reason. Do not abort or discard a successful file for exceeding an estimate.
- Family-level checkpoint keyed by collection scope and family input hash;
  resume skips only matching completed families. Usage includes all content
  reads.
- Evidence lands in `rollouts/<id>/data-map/evidence/<family_id[:12]>/<sha[:12]>`
  (implementation-reference.md §7): full hashes live in the records, and a
  12-hex name already holding other bytes stops with exit 20 instead of
  overwriting.
- Update-period inference: from mtime gaps of existing members or repeated
  inventory evidence. Preserve internal/source time, file mtime, and inventory
  time separately. At least three normalized member timestamps are required to
  record observed gaps and an inferred cadence; weaker evidence → `unknown`.
  A second pass supplies change state, not by itself a periodic or static
  lifecycle. Do not emit expected-gap records in version 1.
- `tests/test_budgets.py`: parametrized over every key in
  `rollout.json.budgets` that letters 05 and 07 enforce (entries, depth,
  wall time, download files, per-file bytes, total bytes): assert the
  matching boundary behavior in implementation-reference.md §2. Per-file
  sizes are advisory; aggregate exhaustion ends content collection. No
  prohibited transfer occurs. Rate limits are tested as pacing, not as
  cumulative request exhaustion.

## Done when

```
python -m pytest -q tests/test_sampling.py tests/test_budgets.py
```

Covers: the 100-file `pattern` fixture yields exactly 5 samples — the three
latest eligible members (its newest file is protected, so they are the 2nd to
4th newest) plus two hash-ranked older ones; a `loose` family of ten yields 3;
two runs pick the same paths; a family with fewer eligible members yields
fewer samples with reasons; unknown-mtime members are never among the latest
three but may be ranked picks; total-bytes budget stops before the next
download; the large eligible fixture produces whole evidence and an
actual-byte/overrun record, and no evidence file is a partial copy; deny
pattern produces no evidence file; newest file is `active_candidate` with no
download; a file that changed between two passes is `active_candidate` even
when it is not the newest; identical files produce one evidence file and no
extra download; a planted evidence file with other bytes under the same
12-hex name makes sampling exit 20 without overwriting it; interrupted
sampling resumes without re-downloading finished families; period is
`unknown` when fewer than three members exist.

Also assert that two unchanged passes remain `change_state: unchanged` with
`lifecycle: unknown`, rather than becoming `static-reference`.

Also cover sample budgets across restart and changed scope/input invalidating
completed family checkpoints. A protected newest file stays protected after
pass 2.
