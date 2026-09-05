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
- `stage 4 next` regenerates both, updates the manifest, stops if any
  family lacks stage 2 interpretation.

## Done when

```
python -m pytest -q tests/test_publish.py
```

Covers: every wiki page and RAG chunk contains at least one evidence sha
that exists in `evidence/`; low-confidence facts never appear in `fact`
chunks; output is byte-deterministic; stage 4 `plan` is refused without
stage 3 result approval.
