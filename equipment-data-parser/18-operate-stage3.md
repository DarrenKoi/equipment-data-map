# Letter 18: Operate: stage 3 pilot on one equipment

## Goal

The first read-only pass over one approved real equipment with narrow roots
and small budgets. The rollout starts here: stages 1 and 2 are the build
tests of letters 03–13, not rollouts (spec §5, §8). This is where the file
structure of the equipment is actually mapped and every new family gets its
bounded LLM interpretation.

## Read

`spec.md` §5 (operating rules, init reconfiguration), §4.6, §8 stage 3,
§6, §9 row for stage 3.

## Rules for letters 18–20

- You run only `preflight`, `status`, `stage N plan`, `stage N next`, and
  `init` where a letter says so — always with flags, never interactively.
- Relay the exit code and the `NEXT:` line verbatim. Exit `10`: append a
  `waiting` line and stop. Exit `20` or `30`: append `blocked` with the
  CLI's reason and stop. Never craft a workaround command.
- The engineer runs every `operator` command in their own terminal. Tell
  them what to run and what hash they will be asked to confirm; never run
  it yourself. `init --equipment <path>` is yours: the path comes from
  `engineer.toml [equipment]` or from the engineer in chat (index.md); you
  never open the file.
- The rollout is the one index.md Loop step 1 selects from `engineer.toml
  [equipment]` and `equipment-map status`: the first equipment file's
  stem without a finished rollout. Below it is written `<id>`: put the id itself in every
  command that takes `--rollout` — `plan`, `next` and `status`; `preflight`
  takes none — and as the `rollout: <id>` field of every ledger line.
- Resume in a later session with `equipment-map status --rollout <id>`.
  The audit ledger, not this file, says where the rollout is.
- You read stdout, `status` output, and `REPORT.md` only. `data-map/`,
  `evidence/`, and `work/` are for the engineer; sample content stays out
  of your context.

A successful `next` waits for result review; do not call it in a loop.
Resume from `status`: unplanned → plan; awaiting plan approval → wait;
plan approved and run incomplete → next once; run complete → wait for result
review; result approved → finish this letter. Re-running `plan` must not erase
an unchanged approval. `status` shows current stage and per-stage approval
history, so approval of stage 3 may show current stage 4.

## Steps

1. Preconditions the engineer confirms before anything runs: firewall and
   access approval done, a read-only account exists, and its credential is
   in the OS keystore under an alias. You never check or change any of these.
2. Run `equipment-map status --rollout <id>`. When it does not know the
   rollout, run `equipment-map init --equipment <dir>/<stem>.toml` with the
   file index.md Loop step 1 selected. While `[equipment]` is missing or
   the file does not exist, append `waiting` naming what is missing with
   the check `[ engineer.toml -nt office/progress.md ]` and stop. `init`
   writes the host, port, roots and credential alias and starts the rollout
   at stage 3; `status` shows stages 1 and 2 as `build`. Budgets, patterns,
   `max_passes`, profile and access window are the spec §5 defaults, and
   the credential is in the keystore from the equipment file. Only if the
   engineer asks for a narrower run do they change a value in
   `rollout.json` before `plan`; you never suggest it. The `llm` block was
   written with defaults by `init`; the endpoint and key are
   `OPENAI_BASE_URL` and `OPENAI_API_KEY` in your harness environment,
   never in a file. When `preflight --stage 3` in step 3 exits 30 for a
   missing `OPENAI_BASE_URL`, append `blocked` naming the variable and
   stop; the engineer sets it in the harness.
3. `equipment-map preflight --stage 3 --contract 1`, then
   `equipment-map stage 3 plan --rollout <id>`. Report the hash and
   the window it includes; append `waiting` until `operator approve-plan`.
4. Run `equipment-map stage 3 next --rollout <id>` once. On
   exit `20` for a connection failure, relay that a diagnostic file exists
   under the rollout directory and stop; the engineer decides.
5. Report the counts: files listed, families, samples, extracted,
   unreadable, budget stops, families interpreted, families `unresolved`,
   passes run and the pass termination reason (`no-eligible-work`,
   `max-passes` or `budget`; only the first means no eligible work is left,
   none means accuracy).
   Report the hash of `llm-provenance.json` from stdout; the model id stays
   in that file. This is the first real LLM interpretation, so ask the
   engineer first to check one measurement family and one log family in
   `file-families.json` against the evidence and confirm the model id and
   config in `data-map/llm-provenance.json`.
   Then ask them to review family accuracy, sample representativeness,
   equipment load, and `coverage.json` (inventory frontier, sample coverage,
   unresolved interpretations by reason). Exit 0 is not proof of complete
   equipment coverage. Before they approve: if they want wider roots or
   bigger budgets, that is another `init` on the same rollout and a new
   plan hash; repeat from step 3. Host, port, protocol and equipment id
   are fixed once step 4 has run: `plan` refuses a change (exit 20), and a
   different equipment needs a new rollout. Once satisfied they run
   `operator approve-result`; after that, widening needs a new rollout.
   Append `waiting`.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 3 result approved. Record the counts only, no equipment
identifier or path, in the `done` line.
