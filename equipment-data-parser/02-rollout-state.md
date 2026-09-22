# Letter 02: Rollout state, plan, approvals, lock

## Goal

The whole control plane with no pipeline inside it yet: `init` writes
`rollout.json`, `plan` hashes it, operators approve, `next` refuses to run
without approval, and `audit.jsonl` is the only state.

## Read

`spec.md` §5 (init, plan, next, operator commands), §5.1 (directory layout,
state truth), §6 (safeguards), §8 opening paragraph (approval per stage).

## Build

Read implementation-reference.md §2–3 before defining schemas or state.

- `equipment_map/rollout.py`: paths for `rollouts/<id>/` files in §5.1.
  Every `--rollout` id must match `[a-z0-9][a-z0-9-]{0,31}` (spec §5.1);
  refuse any other id with exit 20 before touching the filesystem.
- `rollout.json` schema and validation, top-level keys exactly:
  `equipment_id`, `protocol` (`ftp`; the only value the CLI accepts today),
  `host`, `port`, `allowed_roots`, `realtime_candidates`, `allow_patterns`,
  `deny_patterns`, `budgets` (every §4.4 budget plus `llm_max_requests`),
  `max_passes` (integer >= 1, default 1; spec §4.4.1 — a pass ceiling, not
  a budget), `credential_alias`, `access_window` (`always` or `{start, end}` UTC),
  `profile`, `llm` (`glossary_path`,
  `glossary_version`, `model`, `temperature`, `max_tokens`,
  `connect_timeout_seconds`, `request_timeout_seconds`, `max_elapsed_seconds`,
  `transport_max_attempts`, `retry_backoff_seconds`, `prior_max_bytes`
  (integer >= 1, spec §4.6), optional `retention_location`), `next_profile`
  (optional). Missing budgets fail validation (§6 "no budget, no run").
  `init` requires everything except `llm` and `next_profile`; `stage N plan`
  refuses when the fields that stage needs are absent (`llm` from stage 2,
  `next_profile` at stage 5). `retention_location`, when set, must not
  resolve under the rollouts dir.
- `init --rollout <id>`: takes the spec §5 flags — `--equipment-id`,
  `--host`, `--root` (repeatable), optional `--port`, `--protocol`,
  `--baseline`, `--next-profile` — and writes every other key with the spec
  §5 default (an empty `allow_patterns` means everything under
  `allowed_roots`; `llm.model` is `OPENAI_MODEL` from the environment;
  `llm.glossary_path` is the profile's bundled glossary; `glossary_version`
  is the first 12 hex of that file's SHA-256). No LLM endpoint or key is
  stored anywhere: letter 11's client reads `OPENAI_BASE_URL` and
  `OPENAI_API_KEY` from the environment at call time. Defaults land in the
  file like any other value, so `plan` hashes them and a hand edit changes
  them. With a required flag missing, prompt for it when stdin is a TTY;
  otherwise print the missing flag names and exit 20. On an existing rollout it is a
  reconfiguration: refuse when `.lock` exists (exit 20); otherwise prompt
  only for the keys the current stage may change (spec §5 table,
  implementation-reference.md §3), with current values as defaults, copy
  every other value unchanged, write the new file, and append an `init`
  audit record with `old_hash` and `new_hash` of `rollout.json`. While
  stage 4 is current there is nothing to change: exit 20 without writing. Current
  stage = the stage after the highest stage with an `approve-result`. Each
  `init` opens a new epoch for the current stage: `status` ignores that
  stage's `plan`, `approve-plan`, and `next-*` records older than the
  latest `init`, so plan, approval, and next run again. No `init` ever
  invalidates an `approve-result`. `plan.json` is deleted on `init`.
- `audit.jsonl`: append-only records `{ts, event, ...}`. Events at minimum:
  `init`, `plan`, `approve-plan`, `next-start`, `next-stop`, `approve-result`,
  `lock`, `unlock`. `status` reads the ledger and derives current stage and
  approval state. Work databases hold scoped pipeline checkpoints, not
  stage/approval authority. No `state.json` anywhere.
- `stage N plan --rollout <id>`: canonical JSON of the plan (sorted keys,
  stage, rollout.json content, contract) → `plan.json` with `plan_hash`.
  Refuse when stage `N-1` has no `approve-result` (`N=1` needs none).
  Exit 10, `NEXT: WAIT-APPROVAL`.
- `operator approve-plan --rollout <id>`: TTY only. Record OS user, host,
  UTC time, `plan_hash`, and the literal note that this is operator
  self-attestation, not a signature. Prompt shows the hash the operator is
  approving.
- `stage N next --rollout <id>`: refuse without approval (exit 10). Refuse
  when the current `plan.json` hash differs from the approved hash (exit 20).
  Take `.lock` with host, PID, UTC time; refuse when a lock exists (exit 20,
  show lock contents). Release only a lock acquired by this call, on handled exits; a crash leaves it for the engineer. For now the body
  refuses unimplemented stages with exit 20. A completed fake pipeline exists only in tests; no installed placeholder may record `completed: true`. Calling
  `next` on a completed stage is a no-op exit 0 printing result-approval
  state.
- `status --rollout <id>` also prints one line `REPORT.md: absent` or
  `REPORT.md: <sha256>`.
- `equipment_map/manifest.py:write_manifest(rollout_dir)`: writes
  `result-manifest.json` per §5.1 (empty list when `data-map/` is empty) and
  returns its hash. Every `stage N next` calls it once, last thing before
  `next-stop`, so the manifest always matches `data-map/` on disk.
- `operator approve-result --rollout <id>`: TTY only. Records the current
  `result-manifest.json` hash the same way as plan approval. Refuse (exit 20)
  unless the latest current-epoch `next-stop` has `completed: true` and the
  actual file list and rehashed bytes match the manifest and completion hash.
  Apply spec §5.2 to all mutations, past/future-stage calls and input validation.
- `operator unlock --rollout <id>`: TTY only. Shows the lock, asks for
  confirmation, records `unlock` with the old lock contents.
- `NEXT:` lines from `plan` and `next` may name only `stage N plan`,
  `stage N next`, `status`, `WAIT-APPROVAL`, or `STOP`. Operator commands and
  `init` never appear.

- Validate the LLM settings using spec §4.6; include every setting and the
  profile/glossary content hashes in the approved plan. Changed referenced
  files invalidate execution approval too. Do not silently change models.
- `stage N plan` also refuses (exit 20) when a key the stage may not change
  differs from its baseline, naming the keys but never their values. The
  baseline, the `config_hashes` each `plan` record carries, and the stage 3
  identity lock after its first `next-start` are pinned in
  implementation-reference.md §3. A hand-edited `rollout.json` gets the same
  check as one written by `init`.
- Implement spec §5.1 collection scopes exactly as implementation-reference.md
  §3 pins them: the scope ID formula, which `init` epoch counts, and the
  source hash inputs. Checkpoints carry that scope. Stages 2, 4 and 5 bind the
  `scope` and `manifest_hash` of the preceding stage's `approve-result` into
  their plan. The first stage 1 or 3 `next` of a new scope moves the old
  `data-map/` to `work/history/<old scope[:12]>/`, resumably; old audit
  approvals remain intact. A process restart alone changes neither scope nor
  cumulative budgets.
- Baseline adoption (spec §5): every `next-stop` carries `code_hash`, and the
  `init` that creates a rollout may adopt stages 1 and 2 from a baseline
  rollout, starting the new one at stage 3. `code_hash`, the three adoption
  conditions, the `adopt` record and the stage 3 binding are pinned in
  implementation-reference.md §3.

## Done when

```
python -m pytest -q tests/test_rollout_state.py
```

That file covers, with a fake TTY and a temp rollouts dir: init without
flags refuses non-TTY; plan without prior result approval is refused; next before
approve-plan exits 10; next after plan change exits 20; concurrent lock
exits 20; unlock is TTY-only; stage 2 plan before stage 1 result approval is
refused; `status` derives stage from the ledger alone; no `NEXT:` line ever
contains `operator` or `init`; `init` on a locked rollout exits 20; `init`
reconfiguration while stage 2 is current (planned, approved, and run but
not result-approved) keeps stage 1 approved, makes stage 2 unplanned, removes
`plan.json`, and records old and new hashes; `status` prints the
`REPORT.md:` line; `plan` at
stage 2 is refused while `llm` is absent; `retention_location` inside the
rollouts dir fails validation.

Also cover LLM setting and profile/glossary content changes invalidating the
plan, invalid numeric limits, and restart retaining scope and usage counters.
Also cover file mutation/addition/deletion without manifest edits; approval
before completion; stale/future-stage calls; init after terminal completion;
lock collision preserving the owner's lock; malformed audit records; concurrent
plan/init/approval; and repeated plan preserving a valid approval when unchanged.

Also cover the `init` flags: a fresh stage 1 `init --equipment-id x --host
h --root /a` with no TTY writes a `rollout.json` that passes validation with
every spec §5 default in place and never prints `missing required value` or
`missing budget`; the same call without `--host` and without a TTY exits 20
naming `--host`; with `OPENAI_MODEL` set `llm.model` carries it. Also cover
the per-stage `init` table: at stage 2 `init` accepts no equipment flags,
and a hand-edited `host` makes
`stage 2 plan` exit 20 naming `host` with no host value on stdout; at stage 3
an identity change is accepted before the first `next-start` and refused by
`plan` after it, while a roots or budgets change after it is accepted; `init`
at stage 4 exits 20 and leaves `rollout.json` byte-identical; at stage 5 any
change but `next_profile` makes `plan` exit 20. Scope: a stage 2 `init` keeps
the stage 1 scope ID; a stage 3 re-`init` yields a new one; a crash after the
`data-map/` move but before `work/scope.json` is written resumes without a
second move; a rollout id with `/`, `..`, upper case or 33 characters exits 20.

Also cover adoption, with `code_hash` and host injected: a baseline whose own
stages 1 and 2 are result-approved on this host under the current `code_hash`
yields a rollout whose `status` shows both stages `adopted` and current stage
3, with the baseline's `llm` block in `rollout.json` and the adoption in the
stage 3 plan payload. A baseline missing its stage 2 approval, approved on
another host, run under another `code_hash`, or itself adopted makes `init`
exit 20 and leaves no rollout directory. `init` on an existing rollout never
asks for a baseline.
