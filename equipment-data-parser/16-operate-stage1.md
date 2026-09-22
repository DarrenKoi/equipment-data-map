# Letter 16: Operate: stage 1 on the fake tree

## Goal

Run one rollout against the fake FTP tree using
only the commands a stage 1 skill may use. From here on you are the
operator's agent, not the developer: run fixed commands, relay results,
wait for approvals.

## Read

`spec.md` §5 (operating rules), §8 stage 1, §9 table row for stage 1.

## Rules for letters 16–20

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
  [equipment]` and `equipment-map status`: the fixture rollout
  `fixture-<code_hash[:8]>` while no baseline exists, else the first
  equipment file's stem. Below it is written `<id>`: put the id itself in every
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
history, so approval of stage 1 may show current stage 2.

## Steps

1. Run `equipment-map status --rollout <id>`. When it shows stage 1
   `adopted <baseline>`, this is a real equipment's rollout that took
   stages 1 and 2 from the fixture rollout (spec §5): append this letter's
   `done` line with `adopted <baseline>` as its result and go on to letter
   17. When it does not know the rollout, no `init` has run yet: go to
   steps 2 and 3.
2. Prerequisite the engineer performs in their own terminal: start the
   fixtures with `python -m tests.fixtures.serve --write <fixture path>`
   (letter 03), which also writes the fixture's equipment file. For FTP on
   Windows use the local fake proxy, never the office production proxy; see
   engineer-guide.md §2. You start no server. Both adapters have already
   passed build tests; this rollout selects one protocol.
3. Run `equipment-map init --equipment <engineer.toml [equipment] fixture>`
   for the fixture rollout, or `--equipment <dir>/<stem>.toml` for a real
   one (index.md Loop step 1 says which). While `[equipment]` is missing or
   the file does not exist, append `waiting` naming what is missing with
   the check `[ engineer.toml -nt office/progress.md ]` and stop. Budgets
   are defaults; the engineer edits `rollout.json` for smaller ones.
4. `equipment-map preflight --stage 1 --contract 1`, then
   `equipment-map stage 1 plan --rollout <id>`. Report the plan
   hash. Append `waiting` until the engineer has run `operator approve-plan`.
5. Run `equipment-map stage 1 next --rollout <id>` once.
   Report counts.
6. Ask the engineer to review `file-families.json` and `unreadable.json`
   and run `operator approve-result`. Append `waiting`.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 1 in history with plan approved, run completed and result approved,
or `adopted` (current stage is now 2, or 3 when adopted).
Record the counts in the `done` line.
