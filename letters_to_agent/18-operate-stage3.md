# Letter 18: Operate: stage 3 pilot on one equipment

## Goal

The first read-only pass over one approved real equipment with narrow roots
and small budgets, in the same rollout that passed stages 1 and 2. This is
where the file structure of the equipment is actually mapped and every new
family gets its bounded LLM interpretation.

## Read

`spec.md` §5 (init reconfiguration), §8 stage 3, §6, §9 row for stage 3.
Rules from letter 16 apply.

`ROLLOUT` is the rollout id from letter 16's `done` line. The engineer
supplies it in your environment before this letter (for example
`export ROLLOUT=<that id>` in the shell that launches you); you never run
`export` yourself.

## Steps

1. Preconditions the engineer confirms before anything runs: firewall and
   access approval done, a read-only account exists, and its credential is
   in the OS keystore under an alias. You never check or change any of these.
2. Engineer runs `equipment-map init --rollout "$ROLLOUT"` again on the
   same rollout and enters: host, port, share, allowed roots, real-time
   candidate paths, allow/deny patterns, budgets including
   `llm_max_requests`, credential alias, profile name, access window
   (`always` if none). The CLI refuses while a `.lock` exists.
3. `equipment-map preflight --stage 3 --contract 1`, then
   `equipment-map stage 3 plan --rollout "$ROLLOUT"`. Report the hash and
   the window it includes; append `waiting` until `operator approve-plan`.
4. `equipment-map stage 3 next --rollout "$ROLLOUT"` until exit `0`. On
   exit `20` for a connection failure, relay that a diagnostic file exists
   under the rollout directory and stop; the engineer decides.
5. Report the counts: files listed, families, samples, extracted,
   unreadable, budget stops, families interpreted, families `unresolved`.
   Ask the engineer to review family accuracy, sample representativeness,
   equipment load, and `coverage.json` (inventory frontier, sample coverage,
   unresolved interpretations by reason). Exit 0 is not proof of complete
   equipment coverage. Before they approve: if they want wider roots or
   bigger budgets, that is another `init` on the same rollout and a new
   plan hash; repeat from step 3. Once satisfied they run
   `operator approve-result`; after that, widening needs a new rollout.
   Append `waiting`.

## Done when

```
equipment-map status --rollout "$ROLLOUT"
```

Shows stage 3 result approved. Record the rollout id and counts only, no
equipment identifier or path, in the `done` line.
