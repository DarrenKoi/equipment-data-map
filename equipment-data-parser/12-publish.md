# Letter 12: Wiki, Graph and RAG generation, stage 4 `next`

## Goal

Derive `wiki/`, graph exchange JSONL and RAG claim JSONL from the approved
`data-map/` only, every record citing typed sample or metadata evidence.

## Read

`spec.md` §3 (derived outputs), §4.7, §8 stage 4, §1 questions the map answers.

## Build

- `equipment_map/publish.py`: one Markdown page per family and one index
  under `data-map/wiki/`; `data-map/graph/nodes.jsonl`,
  `data-map/graph/edges.jsonl`, and `data-map/rag/chunks.jsonl` per spec
  §4.7.3. JSONL is UTF-8/LF, one canonical sorted-key JSON record per line,
  deterministically ordered and reproducible from the current canonical map.
- Graph node types are exactly `equipment`, `path`, `file_family`, `field`,
  `claim`. Edges are containment, field/claim support and spec §4.7.1 relation
  types. Validate stable IDs, endpoints, scope, provenance and typed evidence.
  Do not add a graph database client, JSON-LD ontology, causal edge or loader.
- RAG lines are one bounded claim, not one file: `schema_version`, `chunk_id`,
  `claim_id`, `family_id`, `category`, `claim_type`, `text`, typed `evidence`, confidence,
  temporal/validity range, sensitivity, producer/version, `unresolved`, and
  coverage/truncation. Facts use deterministic templates over observed records;
  inference uses only validated LLM fields.
  Metadata-only families cite their metadata-evidence file, show the skip
  reason and "content not inspected", and publish only observed metadata
  as facts. Never invent sample hashes or infer internal fields from paths.
- RAG contains no raw representative file, original log line, FDC/measurement
  row or arbitrary verbatim excerpt. Bound and JSON-escape text and continue to
  treat it as untrusted data at retrieval time. Every citation resolves to an
  observation ID plus sample or metadata SHA, and extract SHA/locator when
  needed; reject unresolvable citations and unsupported causal claims.
- Use spec §4.7.3's exact deterministic node/edge ID formulas. A RAG
  `claim_id` must join to the corresponding graph claim node in both
  directions; sample and metadata citations must join to a current-scope
  observation record.
- Follow spec §4.6: all LLM meanings remain `inferred`, regardless of
  self-reported confidence or a general result approval. Only deterministic
  observations enter RAG chunks marked `fact`; low-confidence and unresolved
  fields render in an "unconfirmed" block. Escape data-origin Markdown/HTML
  and forbid generated external images/links; data cannot become instructions.
- `stage 4 next`: exit 20 if any family lacks both interpretation and an
  `unresolved` record; otherwise regenerate Wiki, graph and RAG, write
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

Covers: every wiki page, graph claim/relation and RAG chunk contains at least one typed evidence
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
Graph and RAG files are byte-identical for fixed input, contain no bulk event or
time-series rows, and reject foreign scope/IDs, missing endpoints, LLM-authored
facts and citations whose locator is absent from the cited extract.
Also reject traversal-order/database-generated graph IDs, missing sample or
metadata observation IDs, and graph/RAG claim IDs that do not match.
