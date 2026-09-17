# Letter 07: Sampling into the local mirror

## Goal

Download only representatives per family, under every download budget,
into a local mirror of the equipment's folders, honouring allow/deny and
`active_candidate`.

## Read

`spec.md` §4.4 in full, §4.7 (local paths and names), §6 (budget stops).

## Build

Use implementation-reference.md §5 for eligibility, hash rank and ties, and
§7 for the local layout, name mapping and download order.

- `equipment_map/localpath.py`: the implementation-reference.md §7 name
  mapping, run over each inventoried listing before sampling from it and
  persisted as §7 says; every later reader (sampling, extraction, data map,
  publish) looks names up there.
- `equipment_map/sampling.py`: per family, pick from the eligible members
  only — never denied, never `active_candidate` (letter 06 flags), never
  omitted by the name mapping:
  - `pattern`: the three latest by `mtime_utc`, then two more by hash rank
    from the remaining eligible members. The latest three show the current
    format; the two ranked picks spread the view over older files.
  - `loose`: up to three by hash rank.
  Hash rank is the deterministic stand-in for random choice, so a resume or
  a rerun over the same inventory picks the same files. Five and three are
  ceilings: fewer eligible members give fewer samples, with reasons.
  Record the skip reason for every protected member; never download one.
- Every transfer goes through letter 03's download guard. Record SHA-256 of
  the downloaded bytes. There is no content dedup: two paths with identical
  bytes are two samples. Every sample is a whole file — nothing is truncated
  (spec §4.1). Large or unknown-size eligible files may be downloaded; record
  actual bytes and per-file advisory overruns. Only failed/skipped transfers
  remain metadata-only.
- Enforce file-count and start-time gates. Total bytes are a best-effort target:
  after a completed download reaches it, stop new downloads and record the
  reason. Do not abort or discard a successful file for exceeding an estimate.
- Family-level checkpoint keyed by collection scope and family input hash;
  resume skips only matching completed families. Usage includes all content
  reads.
- Evidence lands at `rollouts/<id>/data-map/evidence/<mirror>`. Receive,
  record, move, reuse or stop exactly as implementation-reference.md §7
  "Downloads" says; never overwrite.
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
python -m pytest -q tests/test_sampling.py tests/test_budgets.py tests/test_localpath.py
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
when it is not the newest; two paths with identical bytes produce two
evidence files at their own mirror paths; a planted file at a selected
evidence path with no matching record makes sampling exit 20 without
overwriting it; interrupted sampling resumes without re-downloading finished
families, and a crash after the record and before the move resumes by
finishing the move; period is `unknown` when fewer than three members exist.

Name mapping, in `tests/test_localpath.py` with a table of cases: remote
names containing `:`, `%`, `*`, a control character, a trailing dot or space,
`NUL.txt`, `com¹` and `Index.MD` map as implementation-reference.md §7 states;
Korean names pass through unchanged; `Logs/` and `logs/` in one listing keep
`Logs/` and omit `logs/` with its subtree, and sampling sends zero requests for
the omitted content; `/Data/a` and `/data/b` as two roots keep the first and
omit the second; a file whose mirror path passes 85 characters, or a folder
past 80, is omitted as `path-too-long`; after a restart, a newly listed name
that casefolds to an assigned path is omitted and the assigned name stays.

Also assert that two unchanged passes remain `change_state: unchanged` with
`lifecycle: unknown`, rather than becoming `static-reference`.

Also cover sample budgets across restart and changed scope/input invalidating
completed family checkpoints. A protected newest file stays protected after
pass 2.
