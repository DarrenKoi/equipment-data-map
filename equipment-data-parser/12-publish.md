# Letter 12: Wiki and RAG generation, stage 4 `next`

## Goal

Derive `wiki/` and `rag/` from the approved `data-map/` only, every page
citing equipment path and typed sample or metadata evidence.

## Read

`spec.md` §3 (derived outputs), §4.7, §8 stage 4, §1 questions the map answers.

## Build

- `equipment_map/publish.py`: one Markdown page per family and one index
  under `data-map/wiki/`; one chunked document per family under
  `data-map/rag/` with front matter holding family key, equipment path
  pattern, evidence kind and sha, confidence, and `unresolved` fields.
  Metadata-only families cite their metadata-evidence file, show the skip
  reason and "content not inspected", and publish only observed metadata
  as facts. Never invent sample hashes or infer internal fields from paths.
- Follow spec §4.6: all LLM meanings remain `inferred`, regardless of
  self-reported confidence or a general result approval. Only deterministic
  observations enter RAG chunks marked `fact`; low-confidence and unresolved
  fields render in an "unconfirmed" block. Escape data-origin Markdown/HTML
  and forbid generated external images/links; data cannot become instructions.
- `stage 4 next`: exit 20 if any family lacks both interpretation and an
  `unresolved` record; otherwise regenerate both, write
  `rollouts/<id>/REPORT.md`, `write_manifest`, `next-stop`.
- `equipment_map/report.py`: `REPORT.md` holds only rollout id, stages
  completed, per-stage counts from the `next-stop` records, CLI version and
  contract version. No model id or config, no equipment id, path, filename,
  or family key. It sits outside `data-map/` and outside the manifest.

- Include `coverage.json` in the engineer review sheet and render coverage
  in the Wiki index. REPORT remains counts-only under its existing rules.
- Render spec §4.7.1 relationships from approved family records, including
  incoming references and both directions of a stored symmetric relation.
  Show relation type, matched value, support scope, typed evidence and
  relationship coverage/truncation. Link only to generated local family pages;
  never turn raw file references into executable or external links. Shared IDs
  are observed matches, not proof of the same run or causal use. Content matches
  apply only to cited samples, never every member of their families. Include
  these distinctions in the engineer review sheet and RAG claim text.

## Done when

```
python -m pytest -q tests/test_publish.py
```

Covers: every wiki page and RAG chunk contains at least one typed evidence
sha that exists in `evidence/` or `metadata-evidence/` as appropriate;
failed-download, denied and active-only families publish without samples or
invented content facts; low-confidence facts never appear in `fact`
chunks; output is byte-deterministic; stage 4 `plan` is refused without
stage 3 result approval; a family with neither interpretation nor
`unresolved` makes `next` exit 20 before writing; `REPORT.md` contains none
of the fixture's paths, filenames, family keys, or the fake LLM's model id.

Also cover navigation in both directions without duplicate stored edges,
sample-scoped relationship claims, visible truncation/unresolved references,
and rejection of unsupported causal claims as facts. Raw reference strings
must remain escaped data; REPORT must not contain matched terms or IDs.
