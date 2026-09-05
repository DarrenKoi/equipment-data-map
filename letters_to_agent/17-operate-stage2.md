# Letter 17: Operate: stage 2 with the local LLM

## Goal

Add LLM interpretation to the harness rollout and confirm accuracy on one
measurement family and one log family with the engineer.

## Read

`spec.md` §4.6, §8 stage 2, §9 row for stage 2. Rules from letter 16 apply.

## Steps

1. Confirm with the engineer that `rollout.json` names the approved
   internal endpoint and key alias. If not, they re-run `init`; you wait.
2. `preflight --stage 2 --contract 1`, `stage 2 plan`, report hash, wait
   for `operator approve-plan`.
3. `stage 2 next` until exit `0`. Report per-field resolved and
   `unresolved` counts, plus `model_id` and `prompt_version` from stdout.
4. Ask the engineer to check one measurement family and one log family in
   `file-families.json` against the evidence, then `operator approve-result`.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 2 result approved. Record model id, serving config as the
engineer states it, and resolved/unresolved counts in the `done` line.
