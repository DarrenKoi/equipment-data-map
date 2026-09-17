# Letter 11: Local LLM analysis and stage 2 `next`

## Goal

Per-field interpretation through the approved company endpoint, with durable
results, bounded API failures, and explicit interpretation coverage.

## Read

`spec.md` §4.6 in full, §4.7 (retention, metadata evidence, coverage),
§5.1 (collection scope), §8 stage 2.

## Build

Read implementation-reference.md §8 for prompts, field validators and limits.

- `equipment_map/llm/client.py`: use the approved `llm` configuration from
  letter 02, key via `secrets.lookup`. Use the approved internal `http://`
  endpoint; HTTP applies to office deployments and fixtures alike.
  Send `model`, `temperature` and
  `max_tokens`; record requested alias separately from returned model ID,
  revision and serving settings. Unknown backend details remain `unknown`.
  No automatic model switching. No streaming.
- Enforce spec §4.6 transport policy exactly: retry only connection errors,
  timeouts and HTTP 429/502/503/504, at most `transport_max_attempts` (1–3)
  per semantic response slot, with exponential backoff and Retry-After.
  Bound calls and waits by both remaining LLM elapsed time and rollout time.
  Persist cumulative elapsed usage; interrupted in-flight reservations count
  their reserved timeout conservatively. Process downtime causes no requests;
  restart never grants fresh counters. Reserve every HTTP request against
  `llm_max_requests` before sending, including retries and lost responses.
  Budget exhaustion → `unresolved: budget`; exhausted transient retries →
  `unresolved: service-unavailable`; other HTTP errors → `unresolved: api-error`.
  Authentication errors stop further calls and mark remaining fields api-error.
- `equipment_map/llm/fields.py`: one short prompt per field — description,
  data category, field meanings and semantic roles, producer, lifecycle,
  expected period, operational use, sensitivity,
  confidence (`high`|`medium`|`low`), evidence (newline-separated sample
  SHA-256 values from the current family's sample records, assembled into a
  list by code) — each with a validator.
  Input is family rule/stats, bounded extract, extractor structure, glossary,
  and the deterministic sample SHA identifiers needed to cite that bundle.
  From pass 2 (spec §4.6) add a `prior_inferred` data block: the previous
  completed pass's validated `category` and `description` for this family
  and for families linked to it by a validated relationship, each with
  family ID, pass number, value and provenance, capped by
  `llm.prior_max_bytes` (keep this family first, then linked families in
  family-ID order). The prompt states it is a previous inference that may be
  wrong and must be kept, corrected or set to UNKNOWN on current evidence.
  The evidence validator rejects any citation of a prior item; citable
  evidence stays this family's own sample SHAs. Results are `inferred` in
  every pass.
  No sample → skip API calls and mark content interpretation `unresolved:
  no-sample`; metadata evidence comes from the CLI, never the model.
- Validate category against spec §4.7.2's fixed enum and lifecycle against
  `append-series`, `rolling-or-rotating`, `replaced-snapshot`,
  `immutable-per-run`, `static-reference`, `unknown`. LLM-derived category,
  lifecycle, field role and meaning are schema-forced to `inferred`; the model
  cannot address or overwrite any `observed` field. A pathname or two unchanged
  inventories are insufficient evidence for `static-reference`.
- Two semantic response slots per field. A received invalid answer consumes
  one slot; transient transport errors do not. Each slot has the independent
  finite transport limit above. Two invalid answers → `confidence: low`,
  `unresolved: invalid-response`. Any unresolved field has low confidence.
- `work/llm.sqlite`: durable per-field results and request reservations in
  transactions with SQLite synchronous FULL. Key results by collection scope,
  family input SHA (rule, stats, sample/extract hashes, and the Observed
  summary hash of directly linked families), field, and hashes of
  model settings, prompt and glossary. The `prior_inferred` block hash is
  provenance only, never part of the key: an unchanged Observed input is not
  re-requested because the prior changed. Store a reservation before each call;
  commit response disposition, validated field value or unresolved reason,
  provenance and counters in one transaction before advancing. A committed
  valid field is never requested again, even if the family is incomplete.
  An unfinished reservation after a crash counts as used transport capacity;
  continue that slot only within its remaining limits, otherwise unresolved.
  No exactly-once execution claim for the remote API.
- Export `work/llm-attempts.jsonl` atomically from that database, ordered by
  request id, on exit and resume. It is an audit view, not recovery authority.
  Include `{request_id, ts, scope, family_key_sha256, input_sha256, field,
  semantic_slot, transport_attempt, prompt_sha256, response_sha256|null,
  requested_model, model_id, status, failure_reason|null, next_safe_action}`.
  A crash between database commit and export must not lose results or calls.
- Every LLM-derived field carries requested model, returned model ID (or
  unknown), `model_config`, `prompt_version`, `glossary_version`, and
  `observed_vs_inferred`. Save validated interpretation values for the map
  and recovery. Raw prompt/response envelopes are represented by hashes only
  unless approved `llm.retention_location` is set outside `rollouts/`.
  Do not confuse a persisted validated description with raw response logging.
- `data-map/llm-provenance.json`: model provenance, request count, resolved
  and unresolved field counts by reason. Update `coverage.json` with family
  and field interpretation coverage; execution completion never means every
  field resolved. stdout contains counts and hashes only.
- `interpret_families(rollout_dir, keys)` resumes per-field results and marks
  a family complete only when every field has a durable result or unresolved
  disposition. Stage 2 consumes the approved stage 1 collection; letter 13
  uses fresh stage 3 scope. Reconfiguration invalidates mismatched result keys.
- `stage 2 next`: interpret, update coverage/provenance, write manifest, then
  `next-stop`. Continue across unresolved families within the approved limits.
- `tests/fixtures/fake_llm.py`: script valid/invalid responses, delayed replies,
  dropped connections, 429 with Retry-After, 503, 401 and permanent outage.

## Done when

```
python -m pytest -q tests/test_llm.py tests/test_stage2_e2e.py
```

Cover valid fields with provenance; two invalid answers becoming unresolved;
transient failures followed by success without using extra semantic slots;
permanent outage terminating within the exact transport/request/time limits;
Retry-After exceeding the remaining deadline causing no extra call; 401
causing no further calls; request budget 1 leaving later fields unresolved;
no-sample families making zero API calls; missing or foreign sample SHA rejected;
a pass-2 packet carrying `prior_inferred` within `prior_max_bytes`, truncated
linked families in family-ID order when over it; a response citing a prior
item rejected; a deliberately wrong prior against contradicting Observed
leaving the result `inferred` and every observed field untouched.
Also cover invalid category/lifecycle enums and a response that attempts to set
`observed`; the validator rejects the former and the schema makes the latter
unrepresentable. Weak cadence evidence stays unknown even if the model guesses
a period.

Kill at each boundary: before send after reservation, after response before
commit, after commit before export, and before family completion. Recover
committed field values without another call; preserve all request charges;
never exceed two semantic slots or the per-slot transport cap. Change input,
model settings or glossary and verify stale field values are not reused.

Stage 2 plan requires stage 1 approval; its manifest matches regenerated data.
With retention disabled, no raw request/response envelope is written under
rollouts (validated field values are expected). Retention under rollouts is
rejected; approved external retention preserves hashes. stdout includes no
prompt, raw response or model ID. Coverage distinguishes a completed run with
unresolved fields from a fully interpreted map.
