# Letter 11: Local LLM analysis and stage 2 `next`

## Goal

Per-field interpretation of each family through the company OpenAI-compatible
endpoint, assembled and validated by the CLI, with hashes only on disk.

## Read

`spec.md` §4.6 in full, §4.7 (prompt/response retention), §8 stage 2.

## Build

- `equipment_map/llm/client.py`: base URL and key alias from `rollout.json`;
  key via `secrets.lookup`. Timeouts and a request budget. No streaming.
- `equipment_map/llm/fields.py`: one short prompt per field — description,
  field meanings, producer, expected period, operational use, sensitivity —
  each with a validator. Input bundle is the §4.6 list only: family rule and
  stats, bounded extract, extractor structure, glossary.
- Two attempts per field. Second failure → `confidence: low`,
  `unresolved: <reason>`, move on.
- Every LLM-derived field carries `model_id`, `model_config`,
  `prompt_version`, `glossary_version`, and `observed_vs_inferred`.
- Persist only SHA-256 of prompt and response plus model info. A retained
  prompt store exists only when `rollout.json` names an approved location;
  `data-map/` then holds the location id and hashes.
- `stage 2 next`: for each family in the approved stage 1 `data-map/`, fill
  interpretation fields into `file-families.json`; checkpoint per family.
- `tests/fixtures/fake_llm.py`: HTTP server returning scripted responses
  (valid, invalid JSON, timeout).

## Done when

```
python -m pytest -q tests/test_llm.py tests/test_stage2_e2e.py
```

Covers: valid response fills the field with provenance; two invalid
responses yield `unresolved` and the run continues; no prompt or response
text appears under `rollouts/` unless a retention location is configured;
stage 2 `plan` is refused without stage 1 result approval; stdout contains
no prompt text.
