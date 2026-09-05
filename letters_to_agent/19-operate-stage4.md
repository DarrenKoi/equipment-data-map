# Letter 19: Operate: stage 4 publish, the deliverable

## Goal

Generate the Wiki and RAG documents from the reviewed map and hand the
engineer the finished data map.

## Read

`spec.md` §8 stage 4, §4.7, §1 (questions the map must answer). Rules from
letter 16 apply.

## Steps

1. `preflight --stage 4 --contract 1`, `stage 4 plan`, wait for approval.
2. `stage 4 next` until exit `0`.
3. Ask the engineer to open `rollouts/<id>/data-map/wiki/index.md` and
   confirm each family page answers the §1 questions or marks them
   unconfirmed with a reason, then `operator approve-result`.
4. Write the final report to `rollouts/<id>/REPORT.md`: rollout id, stages
   completed, counts per stage, CLI and contract versions, model id and
   config used at stage 2. Nothing else. This is the only summary that may
   leave the company network.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 4 result approved and `REPORT.md` exists. The deliverable is
`rollouts/<id>/data-map/`. Append `done`, then stop and report to the
engineer.
