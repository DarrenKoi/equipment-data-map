# Letter 20: Operate: stage 5 register the next profile

## Goal

Close the rollout by registering the profile the next equipment of this
type will use, and hand the engineer the list of families that still need
an extractor release.

## Read

`spec.md` §8 stage 5, §5 (init reconfiguration), §9 row for stage 5.
Rules from letter 16 apply.

`ROLLOUT` is the rollout id from letter 16's `done` line. The engineer
supplies it in your environment before this letter (for example
`export ROLLOUT=<that id>` in the shell that launches you); you never run
`export` yourself.

## Steps

1. The engineer writes `profiles/<type>.json` for the next equipment type
   (allowed path patterns, filename token rules, mapping to existing
   extractor names) and runs `equipment-map init --rollout "$ROLLOUT"`
   again, entering its name as `next_profile`. You write no profile and no
   extractor code.
2. `equipment-map preflight --stage 5 --contract 1`, then
   `equipment-map stage 5 plan --rollout "$ROLLOUT"`; append `waiting`
   until `operator approve-plan`.
3. `equipment-map stage 5 next --rollout "$ROLLOUT"` until exit `0`.
   Report the counts: extractors mapped, families listed in
   `extractor-requests.json`, and the new `REPORT.md` hash.
4. Ask the engineer to review `data-map/extractor-requests.json` and run
   `operator approve-result`. Append `waiting`. Any new extractor goes
   through a separate CLI release, not this rollout.

## Done when

```
equipment-map status --rollout "$ROLLOUT"
```

Shows stage 5 result approved and a `REPORT.md: <sha256>` line equal to
the hash reported in step 3. Record the rollout id, counts, and that hash
in the `done` line. The rollout is complete; a new equipment of the registered
type starts a new rollout at letter 16 with that profile.
