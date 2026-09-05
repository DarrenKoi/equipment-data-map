# Letter 02: Rollout state, plan, approvals, lock

## Goal

The whole control plane with no pipeline inside it yet: `init` writes
`rollout.json`, `plan` hashes it, operators approve, `next` refuses to run
without approval, and `audit.jsonl` is the only state.

## Read

`spec.md` §5 (init, plan, next, operator commands), §5.1 (directory layout,
state truth), §6 (safeguards), §8 opening paragraph (approval per stage).

## Build

- `equipment_map/rollout.py`: paths for `rollouts/<id>/` files in §5.1.
- `rollout.json` schema and validation: equipment id and protocol, allowed
  roots, real-time candidate paths, sample allow/deny patterns, every budget
  in §4.4, credential alias, access window (`always` or a UTC window).
  Missing budgets fail validation (§6 "no budget, no run").
- `init --rollout <id>`: interactive prompts filling that schema. Refuse when
  stdin is not a TTY (exit 20).
- `audit.jsonl`: append-only records `{ts, event, ...}`. Events at minimum:
  `init`, `plan`, `approve-plan`, `next-start`, `next-stop`, `approve-result`,
  `lock`, `unlock`. `status` reads the ledger and derives current stage and
  approval state. No `state.json` anywhere.
- `stage N plan --rollout <id>`: canonical JSON of the plan (sorted keys,
  stage, rollout.json content, contract) → `plan.json` with `plan_hash`.
  Refuse when stage `N-1` has no `approve-result` (`N=1` needs none).
  Exit 10, `NEXT: WAIT-APPROVAL`.
- `operator approve-plan --rollout <id>`: TTY only. Record OS user, host,
  UTC time, `plan_hash`, and the literal note that this is operator
  self-attestation, not a signature. Prompt shows the hash the operator is
  approving.
- `stage N next --rollout <id>`: refuse without approval (exit 10). Refuse
  when the current `plan.json` hash differs from the approved hash (exit 20).
  Take `.lock` with host, PID, UTC time; refuse when a lock exists (exit 20,
  show lock contents). Release the lock on every exit path. For now the body
  does no work and records `next-stop` with `completed: true`. Calling
  `next` on a completed stage is a no-op exit 0 printing result-approval
  state.
- `operator approve-result --rollout <id>`: TTY only. Records
  `result-manifest.json` hash (write an empty-manifest hash for now) the same
  way as plan approval.
- `operator unlock --rollout <id>`: TTY only. Shows the lock, asks for
  confirmation, records `unlock` with the old lock contents.
- `NEXT:` lines from `plan` and `next` may name only `stage N plan`,
  `stage N next`, `status`, `WAIT-APPROVAL`, or `STOP`. Operator commands and
  `init` never appear.

## Done when

```
python -m pytest -q tests/test_rollout_state.py
```

That file covers, with a fake TTY and a temp rollouts dir: init refuses
non-TTY; plan without prior result approval is refused; next before
approve-plan exits 10; next after plan change exits 20; concurrent lock
exits 20; unlock is TTY-only; stage 2 plan before stage 1 result approval is
refused; `status` derives stage from the ledger alone; no `NEXT:` line ever
contains `operator` or `init`.
