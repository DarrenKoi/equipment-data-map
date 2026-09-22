# Letter 19: Operate: stage 4 publish, the deliverable

## Goal

Generate the Wiki and graph exchange records from the reviewed map and hand
the engineer the finished data map.

## Read

`spec.md` §8 stage 4, §4.7, §1 (questions the map must answer), §5 outbound
summary paragraph. Rules from letter 18 apply.

## Steps

1. `equipment-map preflight --stage 4 --contract 1`, then
   `equipment-map stage 4 plan --rollout <id>`; append `waiting`
   until `operator approve-plan`.
2. Run `equipment-map stage 4 next --rollout <id>` once. It
   writes `wiki/`, `graph/nodes.jsonl`, `graph/edges.jsonl`, and
   `rollouts/<id>/REPORT.md`.
3. Ask the engineer to copy `rollouts/<id>/data-map/wiki/` to a folder
   outside `rollouts/`, open that copy in Obsidian (engineer-guide.md §4),
   and confirm each family section answers the §1 questions or marks them
   unconfirmed with a reason; metadata-only sections must say content was not
   inspected. Review
   inventory, local-mapping, sampling and interpretation coverage in the root
   `index.md` and `coverage.json`. Confirm the Fields examples show no secrets,
   Wiki entries and graph records have resolvable typed citations, and
   nothing contains raw log lines or FDC/measurement rows, then run
   `operator approve-result`. Append `waiting`.
4. Relay `REPORT.md` to the engineer as is. It is the only summary that may
   leave the company network; you write no other summary and add nothing
   to it.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 4 result approved and a `REPORT.md: <sha256>` line. The
deliverable is `rollouts/<id>/data-map/`. Record the per-stage counts from
`REPORT.md` in the `done` line, then continue to letter 20.
