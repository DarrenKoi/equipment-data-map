# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Repo status

Docs only, no code yet. There is no build, lint, or test command. The architecture doc is the spec the code must satisfy. When the `equipment-map` CLI lands, record its build, test, and single-test commands here.

## Where things are

`docs/architecture/equipment-data-map.md` (Korean) is the source of truth. Section map:

| Need | Section |
|---|---|
| Runtime pipeline (6 steps) and module seams (Source, Inventory, Grouping, Sampling, Extraction, LLM, Data Map) | §3, §4 |
| CLI subcommands, exit codes, stdout rules | §5 |
| Rollout directory layout and state truth | §5.1 |
| Safeguards (allowlist, lock, approval hash) | §6 |
| Verification scenarios against fake FTP/SMB | §7 |
| Rollout stages 1–5 | §8 |
| Skill suite layout and per-skill allowed commands | §9 |
| Done criteria and explicit out-of-scope list | §10, §11 |

## Invariants that cut across every file

- **Two stage axes.** The 6-step runtime pipeline runs inside one CLI invocation. The 5 rollout stages are what the six skills map to. Keep them apart.
- **One CLI, thin skills.** All logic lives in `equipment-map`. Each `SKILL.md` runs fixed subcommands only: `preflight --stage N`, `stage N plan`, `stage N next`, `status`. A skill contains no branching, state machine, JSON assembly, or cross-skill call, and there is no `equipment-map-common` skill.
- **`audit.jsonl` is the state.** Append-only ledger under `rollouts/<id>/`; `status` derives the current stage from it. There is no mutable `state.json`.
- **Operator commands stay human.** `init`, `operator approve-plan`, `operator approve-result`, `operator unlock` appear in no skill and in no CLI `NEXT:` line. A skill invoking one is a scenario failure.
- **`rollout.json` is the only input to `plan`.** Roots, budgets, allow/deny patterns, and credential aliases come from that file, never from command flags.
- **Fixed exit contract.** `0` done or safe no-op, `10` await approval, `20` stop, `30` preflight failed. Last stdout line is `NEXT: <command | WAIT-APPROVAL | STOP | INSTALL-OR-UPGRADE>`.
- **stdout carries counts and hashes only.** Paths, filenames, sample content, credentials, and LLM prompts/responses go to files under the rollout directory.
