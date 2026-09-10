# Letter 16: Operate: stage 1 on the fake tree

## Goal

Run one rollout against the selected fake FTP or SMB tree using
only the commands a stage 1 skill may use. From here on you are the
operator's agent, not the developer: run fixed commands, relay results,
wait for approvals.

## Read

`spec.md` §5 (operating rules), §8 stage 1, §9 table row for stage 1.

## Rules for letters 16–20

- You run only `preflight`, `status`, `stage N plan`, `stage N next`.
- Relay the exit code and the `NEXT:` line verbatim. Exit `10`: append a
  `waiting` line and stop. Exit `20` or `30`: append `blocked` with the
  CLI's reason and stop. Never craft a workaround command.
- The engineer runs `init` and every `operator` command in their own
  terminal. Tell them what to run and what hash they will be asked to
  confirm; never run it yourself.
- Resume in a later session with `equipment-map status --rollout "$ROLLOUT"`.
  The audit ledger, not this file, says where the rollout is.
- You read stdout, `status` output, and `REPORT.md` only. `data-map/`,
  `evidence/`, and `work/` are for the engineer; sample content stays out
  of your context.
- Every command that accepts a rollout argument, namely `plan`, `next`,
  and `status`, carries `--rollout "$ROLLOUT"`; `preflight` does not.
  `ROLLOUT` is the id the engineer chose at `init`. The engineer supplies
  it in your environment before the letter starts (they run, for example,
  `export ROLLOUT=<that id>` in the shell that launches you); you never
  run `export` yourself.

A successful `next` waits for result review; do not call it in a loop.
Resume from `status`: unplanned → plan; awaiting plan approval → wait;
plan approved and run incomplete → next once; run complete → wait for result
review; result approved → finish this letter. Re-running `plan` must not erase
an unchanged approval. `status` shows current stage and per-stage approval
history, so approval of stage 1 may show current stage 2.

## Steps

1. Prerequisite the engineer performs in their own terminal: start the
   fixtures with `python -m tests.fixtures.serve` (letter 03) and read the
   printed ports. For FTP on Windows use the local fake proxy, never the office
   production proxy; see engineer-guide.md §2. You start no server. Both adapters
   have already passed build tests; this rollout selects one protocol.
2. Ask the engineer to run `equipment-map init --rollout <id>` of their
   choosing, pointing at `localhost` and those ports, with small budgets,
   and to set `ROLLOUT` to that id in your environment.
3. `equipment-map preflight --stage 1 --contract 1`, then
   `equipment-map stage 1 plan --rollout "$ROLLOUT"`. Report the plan
   hash. Append `waiting` until the engineer has run `operator approve-plan`.
4. Run `equipment-map stage 1 next --rollout "$ROLLOUT"` once.
   Report counts.
5. Ask the engineer to review `file-families.json` and `unreadable.json`
   and run `operator approve-result`. Append `waiting`.

## Done when

```
equipment-map status --rollout "$ROLLOUT"
```

Shows stage 1 in history with plan approved, run completed and result approved
(current stage is now 2).
Record the rollout id and counts in the `done` line.
