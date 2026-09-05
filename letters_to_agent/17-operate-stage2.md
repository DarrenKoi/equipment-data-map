# Letter 17: Operate: stage 2 with the local LLM

## Goal

Add LLM interpretation to the harness rollout and confirm accuracy on one
measurement family and one log family with the engineer.

## Read

`spec.md` §4.6, §8 stage 2, §9 row for stage 2. Rules from letter 16 apply.

`ROLLOUT` is the rollout id from letter 16's `done` line. The engineer
supplies it in your environment before this letter (for example
`export ROLLOUT=<that id>` in the shell that launches you); you never run
`export` yourself.

## Steps

1. Ask the engineer to run `equipment-map init --rollout "$ROLLOUT"` again
   and fill the `llm` block (approved internal endpoint, key alias,
   glossary path/version, requested model, generation limits, timeouts,
   elapsed limit and retry settings from letter 11). You wait; `stage 2 plan` refuses until it
   is present.
2. `equipment-map preflight --stage 2 --contract 1`, then
   `equipment-map stage 2 plan --rollout "$ROLLOUT"`; report the hash and
   append `waiting` until `operator approve-plan`.
3. `equipment-map stage 2 next --rollout "$ROLLOUT"` until exit `0`.
   Report the resolved and `unresolved` counts and the hash of
   `llm-provenance.json` from stdout, nothing else.
4. Ask the engineer to check one measurement family and one log family in
   `file-families.json` against the evidence, confirm the model id and
   config in `data-map/llm-provenance.json`, and resolved/unresolved coverage
   and service failures in `data-map/coverage.json`, then run
   `operator approve-result`. Append `waiting`.

## Done when

```
equipment-map status --rollout "$ROLLOUT"
```

Shows stage 2 result approved. Record the resolved/unresolved counts and
the provenance file hash in the `done` line; the model id stays in the
provenance file.
