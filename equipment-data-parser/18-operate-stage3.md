# Letter 18: Operate: stage 3 pilot on one equipment

## Goal

The first read-only pass over one approved real equipment with narrow roots
and small budgets, in the same rollout that passed or adopted stages 1 and
2. This is where the file structure of the equipment is actually mapped and
every new family gets its bounded LLM interpretation.

## Read

`spec.md` §5 (init reconfiguration), §8 stage 3, §6, §9 row for stage 3.
Rules from letter 16 apply.

## Steps

1. Preconditions the engineer confirms before anything runs: firewall and
   access approval done, a read-only account exists, and its credential is
   in the OS keystore under an alias. You never check or change any of these.
2. Take the real equipment's `id`, `host`, `port` and `roots` from
   `engineer.toml [equipment]` (the engineer replaced the stage 1 fixture
   values; in chat they may give them directly) and run
   `equipment-map init --rollout <id> --equipment-id <id> --host <host> --port <port> --root <r>...`
   on the same rollout — an adopted rollout got this at its first `init`.
   While the table still holds the fixture host, append `waiting` asking
   for the real `[equipment]` and stop. Real-time candidate paths,
   allow/deny patterns, smaller budgets, `max_passes`, credential alias,
   profile and access window are the engineer's hand edits to
   `rollout.json` before `plan`; tell them so once. The CLI refuses while a
   `.lock` exists.
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
   Ask the engineer to review family accuracy, sample representativeness,
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
