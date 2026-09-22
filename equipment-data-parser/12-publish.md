# Letter 12: Wiki and Graph generation, stage 4 `next`

## Goal

Derive the Obsidian-readable `wiki/`, which mirrors the equipment's folders,
and graph exchange JSONL from the approved `data-map/` only, every record
citing typed sample or metadata evidence.

## Read

`spec.md` §3 (derived outputs), §4.7, §8 stage 4, §1 questions the map answers.

## Build

Use implementation-reference.md §7 for the local layout, Wiki pages and links,
the Fields table, masking, escaping and citations.

- `equipment_map/publish.py`: one `index.md` per folder under
  `data-map/wiki/`, at the folder's local path from `paths.json`
  (`wiki/index.md` is `/`), plus `data-map/graph/nodes.jsonl` and
  `data-map/graph/edges.jsonl` per spec §4.7.3. JSONL is UTF-8/LF, one
  canonical sorted-key JSON record per line, deterministically ordered and
  reproducible from the current canonical map.
- Graph node types are exactly `equipment`, `path`, `file_family`, `field`,
  `claim`. Edges are containment, field/claim support and spec §4.7.1 relation
  types. Validate stable IDs, endpoints, scope, provenance and typed evidence.
  Do not add a graph database client, JSON-LD ontology, causal edge or loader.
- Wiki pages are read by people and by LLMs through file tools or the
  Obsidian CLI, walking folder links down from `wiki/index.md`; build them
  exactly as implementation-reference.md §7 "Wiki files" says.
- Family sections render the Fields table: type, unit, range in samples,
  null/invalid counts and up to three example values per field; a field whose
  name looks secret shows neither range nor examples. Each example is one
  field value; rows, log lines and excerpts stay in `evidence/`.
  Metadata-only families cite their metadata-evidence record, show the skip
  reason and "content not inspected", and publish only observed metadata
  as facts. Never invent sample hashes or infer internal fields from paths.
- Render every data-origin string as literal text, so Markdown, HTML and
  Obsidian syntax do not render; generate no external images or links. Literal
  rendering does not stop a reading LLM from following text in a value, so the
  Wiki stays untrusted data for every reader (engineer-guide.md §4). Every
  citation resolves to an observation ID plus sample or metadata SHA, as
  implementation-reference.md §7 "Citations" says, and extract SHA/locator
  when needed; reject unresolvable citations and
  unsupported causal claims.
- Use spec §4.7.3's exact deterministic node/edge ID formulas. Sample and
  metadata citations must join to a current-scope observation record.
- Follow spec §4.6: all LLM meanings remain `inferred`, regardless of
  self-reported confidence or a general result approval. Only deterministic
  observations render under `### Observed`; low-confidence and unresolved
  fields render in an "unconfirmed" block under `### Inferred`.
- `stage 4 next`: exit 20 if any family lacks both interpretation and an
  `unresolved` record; otherwise regenerate Wiki and graph, write `rollouts/<id>/REPORT.md`,
  `write_manifest`, `next-stop`.
- `equipment_map/report.py`: `REPORT.md` holds only rollout id, stages
  completed, per-stage counts from the `next-stop` records, CLI version and
  contract version. Stages 1 and 2 of a rollout that started at
  stage 3 read `build` in place of counts. No model id or config, no equipment id, path, filename,
  or family key. It sits outside `data-map/` and outside the manifest.

- Include `coverage.json` in the engineer review sheet and render coverage,
  local mapping omissions included, in `wiki/index.md`. REPORT remains
  counts-only under its existing rules.
- Render spec §4.7.1 relationships from approved family records, including
  incoming references and both directions of a stored symmetric relation.
  Show relation type, matched value, support scope, typed evidence and
  relationship coverage/truncation. Link only to generated folder pages;
  never turn raw file references into executable or external links. Shared IDs
  are observed matches, not proof of the same run or causal use. Content matches
  apply only to cited samples, never every member of their families. Include
  these distinctions in the engineer review sheet and the Wiki relationship
  rows.

## Done when

```
python -m pytest -q tests/test_publish.py
```

Covers: every wiki Observed/Inferred entry, relationship row and graph
claim/relation contains at least one typed evidence sha that resolves to a
sample file under `evidence/` or a record in `extracts.jsonl` or
`metadata-evidence.jsonl`, and a citation whose full SHA does not match the
rehashed file or record is rejected; failed-download, denied and
active-only families publish without samples or invented content facts;
low-confidence and LLM values never appear under `### Observed`; output is
byte-deterministic; stage 4 `plan` is refused without stage 3 result approval;
a family with neither interpretation nor `unresolved` makes `next` exit 20
before writing; `REPORT.md` contains none of the fixture's paths, filenames,
family keys, or the fake LLM's model id.

Also cover the Wiki as Obsidian reads it: the folders under `wiki/` are
exactly the mapped inventoried folders and their ancestors, each with one
`index.md` and nothing else; every relative link resolves to a
generated page, including a link into a folder stored as `a%3Ab`; a page lists
its immediate subfolders and its own families, never a grandchild; a folder
outside the allowed roots has a page with folder links only; frontmatter has
exactly the three quoted keys; a fixture whose path, field names and values
contain `[[x]]`, `#tag`, `%%`, `$a$`, `==h==`, `|`, a newline, `<b>`, and
values that start or end with a backtick or a space renders all of them
literally inside code spans; a numeric `db_password` field shows `(masked)` in
both range and examples and its value appears nowhere in the Wiki; no field
shows more than three examples or an example over 40 characters; no page
contains a fixture row or log line verbatim.

Also cover navigation in both directions without duplicate stored edges,
sample-scoped relationship claims, visible truncation/unresolved references,
and rejection of unsupported causal claims as facts. Raw reference strings
must remain escaped data; REPORT must not contain matched terms or IDs.
Graph files are byte-identical for fixed input, contain no bulk event or
time-series rows, and reject foreign scope/IDs, missing endpoints, LLM-authored
facts and citations whose locator is absent from the cited extract.
Also reject traversal-order/database-generated graph IDs and missing sample or
metadata observation IDs.

Windows MAX_PATH: after a publish over a fixture with a folder nested past
the limit, no file under `rollouts/<id>/` is longer than 120 characters
relative to that directory, even with its `data-map/` prefix swapped for
`work/history/<12 hex>/`; that folder appears as a `path-too-long` omission,
without a link, in its nearest ancestor's `index.md`.
