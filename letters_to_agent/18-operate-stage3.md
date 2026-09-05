# Letter 18: Operate: stage 3 pilot on one equipment

## Goal

The first read-only pass over one approved real equipment with narrow roots
and small budgets. This is where the file structure of the equipment is
actually mapped.

## Read

`spec.md` §8 stage 3, §6, §9 row for stage 3. Rules from letter 16 apply.

## Steps

1. Preconditions the engineer confirms before anything runs: firewall and
   access approval done, a read-only account exists, and its credential is
   in the OS keystore under an alias. You never check or change any of these.
2. Engineer runs `init --rollout <equipment>-<date>` with: allowed roots,
   real-time candidate paths, allow/deny patterns, budgets, credential
   alias, profile name, access window (`always` if none).
3. `preflight --stage 3 --contract 1`, `stage 3 plan`, report the hash and
   the window it includes, wait for approval.
4. `stage 3 next` until exit `0`. If it exits `20` on connection failure,
   relay the diagnostic file path and stop; the engineer decides.
5. Report the counts: files listed, families, samples, extracted,
   unreadable, budget stops. Ask the engineer to review family accuracy,
   sample representativeness, and equipment load, then `operator
   approve-result`.
6. If the engineer wants wider roots or bigger budgets, that is a new
   `init` and a new plan hash; repeat from step 3.

## Done when

```
equipment-map status --rollout <id>
```

Shows stage 3 result approved. Record the rollout id and counts only, no
equipment identifier or path, in the `done` line.
