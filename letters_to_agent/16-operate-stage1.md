# Letter 16: Operate: stage 1 on the fake tree

## Goal

Run a real rollout, end to end, against the fake FTP and SMB trees using
only the commands a stage 1 skill may use. From here on you are the
operator's agent, not the developer: run fixed commands, relay results,
wait for approvals.

## Read

`spec.md` §5 (operating rules), §8 stage 1, §9 table row for stage 1.

## Rules for letters 16–19

- You run only `preflight`, `status`, `stage N plan`, `stage N next`.
- Relay the exit code and the `NEXT:` line verbatim. Exit `10`: append a
  `waiting` line and stop. Exit `20` or `30`: append `blocked` with the
  CLI's reason and stop. Never craft a workaround command.
- The engineer runs `init` and every `operator` command in their own
  terminal. Tell them what to run and what hash they will be asked to
  confirm; never run it yourself.
- Resume in a later session with `equipment-map status --rollout <id>`.
  The audit ledger, not this file, says where the rollout is.
- Read nothing under `data-map/evidence/` or `work/`. Sample content stays
  out of your context.

## Steps

1. Start the fake FTP and SMB fixtures locally (from letter 03 and 04) and
   tell the engineer the ports.
2. Ask the engineer to run `equipment-map init --rollout harness-<date>`
   pointing at `localhost`, with small budgets.
3. `preflight --stage 1 --contract 1`, then `stage 1 plan --rollout <id>`.
   Report the plan hash. Append `waiting` until the engineer has run
   `operator approve-plan`.
4. `stage 1 next --rollout <id>` until exit `0`. Report counts.
5. Ask the engineer to review `file-families.json` and `unreadable.json`
   and run `operator approve-result`. Append `waiting`.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 1 with plan approved, run completed, and result approved.
Record the rollout id and counts in the `done` line.
