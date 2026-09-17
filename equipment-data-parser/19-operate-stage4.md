# Letter 19: Operate: stage 4 publish, the deliverable

## Goal

Generate the Wiki and graph exchange records from the reviewed map and hand
the engineer the finished data map.

## Read

`spec.md` §8 stage 4, §4.7, §1 (questions the map must answer), §5 outbound
summary paragraph. Rules from letter 16 apply.

`ROLLOUT` is the rollout id from the current rollout's letter 16 `done` line
(after its newest human rollout marker, if one exists). The engineer
supplies it in your environment before this letter (for example
`export ROLLOUT=<that id>` in the shell that launches you); you never run
`export` yourself.

## Steps

1. `equipment-map preflight --stage 4 --contract 1`, then
   `equipment-map stage 4 plan --rollout "$ROLLOUT"`; append `waiting`
   until `operator approve-plan`.
2. Run `equipment-map stage 4 next --rollout "$ROLLOUT"` once. It
   writes `wiki/`, `graph/nodes.jsonl`, `graph/edges.jsonl`, and
   `rollouts/$ROLLOUT/REPORT.md`.
3. Ask the engineer to copy `rollouts/$ROLLOUT/data-map/wiki/` to a folder
   outside `rollouts/`, open that copy in Obsidian (engineer-guide.md §4), and
   confirm each family page answers the §1 questions or marks them
   unconfirmed with a reason; metadata-only pages must say content was not
   inspected. Review inventory/sampling/interpretation coverage in the Wiki
   index and `coverage.json`. Confirm the Fields examples show no secrets,
   Wiki entries and graph records have resolvable typed citations, and
   nothing contains raw log lines or FDC/measurement rows, then run
   `operator approve-result`. Append `waiting`.
4. Relay `REPORT.md` to the engineer as is. It is the only summary that may
   leave the company network; you write no other summary and add nothing
   to it.

## Done when

```
equipment-map status --rollout "$ROLLOUT"
```

Shows stage 4 result approved and a `REPORT.md: <sha256>` line. The
deliverable is `rollouts/$ROLLOUT/data-map/`. Record the rollout id and the
per-stage counts from `REPORT.md` in the `done` line, then continue to
letter 20.
