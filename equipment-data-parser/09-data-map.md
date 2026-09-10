# Letter 09: Data map output and stage 1 `next`

## Goal

Write `data-map/` and `result-manifest.json` from the pipeline, make the
output byte-deterministic, and wire `stage 1 next` to run inventory →
grouping → sampling → extraction end to end without an LLM.

## Read

`spec.md` §4.7, §5.1 (manifest rules), §7 (byte-identical output), §8 stage 1.

## Build

Use implementation-reference.md §7 for common records and hash ordering.

- `equipment_map/datamap.py`: `index.json` (dataset version, per-file
  hashes), `equipment.json`, `file-families.json`, `paths.json`,
  `unreadable.json`. Sorted keys, `\n` line endings, no timestamps other
  than those from the inventory. `wiki/` and `rag/` stay empty until
  letter 12.
- Clock injection: one `now()` in `equipment_map/clock.py` that tests can
  freeze.
- `result-manifest.json`: sorted `/`-separated relative paths under
  `data-map/` with raw-byte SHA-256; `.lock` and `work/` excluded.
- `stage 1 next`: runs the four steps in order with checkpoints, records a
  `next-stop` audit entry with counts (files listed, families, samples,
  extracted, unreadable) and the manifest hash. stdout shows counts and
  hashes only.
- Stage 1 `plan` refuses a `rollout.json` whose equipment host is not
  `localhost`/`127.0.0.1` (spec §8: fake trees only at stage 1).

- Write `metadata-evidence/<family-key-sha256>.json` and `coverage.json`
  per spec §4.7. Metadata references carry `evidence_kind: metadata` and the
  actual metadata file SHA-256; never invent a sample SHA. Include them in
  index/manifest. Scope the entire map to the active collection; no stale
  fake equipment evidence or interpretations may remain in the real map.
  Coverage records inventory completeness/frontier and sampling coverage;
  later stages add interpretation counts without claiming unseen totals.

## Done when

```
python -m pytest -q tests/test_stage1_e2e.py
```

Covers, on both transports against the fake FTP: `plan` → fake approval →
`next` exits 0 and `data-map/` contains the five base JSON files, coverage, metadata evidence
and sample evidence; two runs with the frozen clock give byte-identical
`data-map/*.json` and the same manifest hash; stdout contains no fixture
path or filename; `next` again is a no-op exit 0.
