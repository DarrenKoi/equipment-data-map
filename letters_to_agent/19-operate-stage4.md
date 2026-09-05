# Letter 19: Operate: stage 4 publish, the deliverable

## Goal

Generate the Wiki and RAG documents from the reviewed map and hand the
engineer the finished data map.

## Read

`spec.md` §8 stage 4, §4.7, §1 (questions the map must answer), §5 outbound
summary paragraph. Rules from letter 16 apply.

`ROLLOUT` is the rollout id from letter 16's `done` line. The engineer
supplies it in your environment before this letter (for example
`export ROLLOUT=<that id>` in the shell that launches you); you never run
`export` yourself.

## Steps

1. `equipment-map preflight --stage 4 --contract 1`, then
   `equipment-map stage 4 plan --rollout "$ROLLOUT"`; append `waiting`
   until `operator approve-plan`.
2. `equipment-map stage 4 next --rollout "$ROLLOUT"` until exit `0`. It
   writes `wiki/`, `rag/`, and `rollouts/$ROLLOUT/REPORT.md`.
3. Ask the engineer to open `rollouts/$ROLLOUT/data-map/wiki/index.md` and
   confirm each family page answers the §1 questions or marks them
   unconfirmed with a reason, then run `operator approve-result`. Append
   `waiting`.
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
