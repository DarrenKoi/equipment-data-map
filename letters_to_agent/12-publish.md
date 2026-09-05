# Letter 12: Wiki and RAG generation, stage 4 `next`

## Goal

Derive `wiki/` and `rag/` from the approved `data-map/` only, every page
citing equipment path and evidence sample.

## Read

`spec.md` §3 (derived outputs), §4.7, §8 stage 4, §1 questions the map answers.

## Build

- `equipment_map/publish.py`: one Markdown page per family and one index
  under `data-map/wiki/`; one chunked document per family under
  `data-map/rag/` with front matter holding family key, equipment path
  pattern, evidence sha, confidence, and `unresolved` fields.
- Facts with `confidence: low` or `unresolved` render in a separate
  "unconfirmed" block and are excluded from RAG chunks marked `fact`.
- `stage 4 next`: exit 20 if any family lacks both interpretation and an
  `unresolved` record; otherwise regenerate both, write
  `rollouts/<id>/REPORT.md`, `write_manifest`, `next-stop`.
- `equipment_map/report.py`: `REPORT.md` holds only rollout id, stages
  completed, per-stage counts from the `next-stop` records, CLI version and
  contract version. No model id or config, no equipment id, path, filename,
  or family key. It sits outside `data-map/` and outside the manifest.

## Done when

```
python -m pytest -q tests/test_publish.py
```

Covers: every wiki page and RAG chunk contains at least one evidence sha
that exists in `evidence/`; low-confidence facts never appear in `fact`
chunks; output is byte-deterministic; stage 4 `plan` is refused without
stage 3 result approval; a family with neither interpretation nor
`unresolved` makes `next` exit 20 before writing; `REPORT.md` contains none
of the fixture's paths, filenames, family keys, or the fake LLM's model id.
