# Letter 11: Local LLM analysis and stage 2 `next`

## Goal

Per-field interpretation of each family through the company OpenAI-compatible
endpoint, assembled and validated by the CLI, with hashes only on disk.

## Read

`spec.md` §4.6 in full, §4.7 (prompt/response retention), §8 stage 2.

## Build

- `equipment_map/llm/client.py`: `llm.endpoint` and `llm.key_alias` from
  `rollout.json`; key via `secrets.lookup`. Timeouts and the
  `budgets.llm_max_requests` budget; when it is spent, remaining fields are
  `unresolved: budget` and the run continues. No streaming.
- `equipment_map/llm/fields.py`: one short prompt per field — description,
  field meanings, producer, expected period, operational use, sensitivity,
  confidence (`high`|`medium`|`low`), evidence (list of SHA-256 that must
  exist under that family's `evidence/` dir) — each with a validator. Input bundle is the §4.6 list only: family rule and
  stats, bounded extract, extractor structure, glossary.
- Two attempts per field. Second failure → `confidence: low`,
  `unresolved: <reason>`, move on. Every attempt appends one record to
  `rollouts/<id>/work/llm-attempts.jsonl` before the next call:
  `{ts, family_key_sha256, field, attempt, prompt_sha256, response_sha256,
  model_id, status, failure_reason|null, next_safe_action}`. Resume reads
  it and never re-asks a field that already has two records.
- Every LLM-derived field carries `model_id`, `model_config`,
  `prompt_version`, `glossary_version`, and `observed_vs_inferred`.
- Persist only SHA-256 of prompt and response plus model info. A retained
  prompt store exists only when `llm.retention_location` is set; it lives
  there, never under `rollouts/` (the client refuses to write prompt or
  response text to any path under the rollouts dir even when configured),
  and `data-map/` holds the location id and hashes.
- `data-map/llm-provenance.json`: `model_id`, `model_config`,
  `prompt_version`, `glossary_version`, request count, per-field resolved
  and `unresolved` counts. This is what the engineer reviews; stdout
  prints only counts and the file's hash.
- `equipment_map/llm/interpret.py:interpret_families(rollout_dir, keys)`:
  the per-family loop above with a per-family checkpoint. Letter 13 reuses
  it at stage 3.
- `stage 2 next`: `interpret_families` over every family in the approved
  stage 1 `data-map/`, then `write_manifest`, then `next-stop`.
- `tests/fixtures/fake_llm.py`: HTTP server returning scripted responses
  (valid, invalid JSON, timeout).

## Done when

```
python -m pytest -q tests/test_llm.py tests/test_stage2_e2e.py
```

Covers: valid response fills the field with provenance; two invalid
responses yield `unresolved` and the run continues; stage 2 `plan` is refused without stage 1 result approval; the manifest
hash after stage 2 differs from the stage 1 hash and matches a fresh
`write_manifest`; a request budget of 1 leaves every later field
`unresolved: budget`; an evidence response naming a sha not in
`evidence/` is invalid; an interrupted run resumes from
`llm-attempts.jsonl` with no third attempt for any field; a
`retention_location` under the rollouts dir fails validation; with no
retention, and with retention at a temp dir outside it, no prompt or
response text exists anywhere under `rollouts/`; stdout contains no prompt
text and no `model_id` value.
