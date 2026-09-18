# Letter 17: Operate: stage 2 with the local LLM

## Goal

Add LLM interpretation to the harness rollout and confirm accuracy on one
measurement family and one log family with the engineer.

## Read

`spec.md` §4.6, §8 stage 2, §9 row for stage 2. Rules from letter 16 apply.

## Steps

1. Run `equipment-map status --rollout <id>`. When it shows stage 2
   `adopted <baseline>`, append this letter's `done` line with
   `adopted <baseline>` as its result and go on to letter 18.
2. Ask the engineer to run `equipment-map init --rollout <id>` again
   and fill the `llm` block (approved internal endpoint, key alias,
   glossary path/version, requested model, generation limits, timeouts,
   elapsed limit, retry settings and `prior_max_bytes` from letter 11). You wait; `stage 2 plan` refuses until it
   is present.
3. `equipment-map preflight --stage 2 --contract 1`, then
   `equipment-map stage 2 plan --rollout <id>`; report the hash and
   append `waiting` until `operator approve-plan`.
4. Run `equipment-map stage 2 next --rollout <id>` once.
   Report the resolved and `unresolved` counts and the hash of
   `llm-provenance.json` from stdout, nothing else.
5. Ask the engineer to check one measurement family and one log family in
   `file-families.json` against the evidence, confirm the model id and
   config in `data-map/llm-provenance.json`, and resolved/unresolved coverage
   and service failures in `data-map/coverage.json`, then run
   `operator approve-result`. Append `waiting`.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 2 result approved, or `adopted`. Record the resolved/unresolved
counts and the provenance file hash in the `done` line; the model id stays
in the provenance file.
