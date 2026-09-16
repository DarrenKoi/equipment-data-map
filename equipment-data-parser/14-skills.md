# Letter 14: Skill suite and installers

## Goal

The six `SKILL.md` files, the suite layout, and the two installers, with a
lint test that proves each skill uses only its allowed commands.

## Read

`spec.md` §9 in full (layout, table, rules), §5 (`NEXT:` contract the skills
relay).

Rules the skills must honour beyond the spec: state and safety decisions
live in scripts, never in skill prose; a skill guides the model and the CLI
fails closed on unsafe or invalid transitions; tool-specific install
metadata stays out of the shared skill body.

## Build

Read implementation-reference.md §9 for installation and scenario evidence.
The run skill has no stage prerequisites; it permits contract preflight and
status listing without a rollout. Do not apply stage-only flags to that skill.

- `equipment-map-suite/` exactly as the §9 tree. `runtime/equipment-map`
  is a thin launcher for the Python package.
- Each `SKILL.md`: frontmatter `name` and `description` only. Body has
  exactly these `##` headings in order: `Role`, `Prerequisites` ("the engineer has supplied a rollout id and
  completed the human gate for the previous stage"), `Commands` (the allowed
  commands verbatim with `--rollout "$ROLLOUT"`, and `ROLLOUT` defined as
  the id the engineer gives), `Reading results` (exit code and `NEXT:`
  table; the single allowed branch: preflight failure → relay the install
  hint and stop), `Checkpoint` (the `status` line expected before and after
  this stage), `Review sheet` (files the engineer reviews by name, ending "then the
  engineer completes the human gate"), `Stop conditions` (exit 10, 20, 30,
  lock present, outside access window: relay and stop), `Completion
  evidence` (the `status` output and audit events that prove the stage),
  and `What you read` ("stdout, `status` output, and `REPORT.md` only;
  `data-map/`, `evidence/`, and `work/` are for the engineer"). Stage
  descriptions name stage number, role, and unique task; only
  `equipment-map-run` is broad. A skill never names or shows `init`,
  `operator`, `approve-plan`, `approve-result`, `unlock`, or `workbench`;
  it says "human gate" instead.
- Discovery roots are suite-version contract values stored in
  `VERSION.json` under `discovery`, one per tool, relative to `$HOME` or
  `%USERPROFILE%`. All four stay in the contract as install targets even
  though letter 15 validates pi only; the other three are pre-wired for the
  later extension, not a claim that they are supported.
  Before writing the installers, append `waiting` with
  the candidate values (Codex `.codex/skills`, Claude Code
  `.claude/skills`, OpenCode `.config/opencode/skills`, pi
  `.pi/agent/skills`) and stop until `office/progress.md` holds a human line
  `14 confirmed <UTC date> | discovery: <four values>`.
- `install/install.sh` and `install/install.ps1`, same behaviour: read the
  roots from `VERSION.json`, copy each skill to `<root>/<skill-name>/` and
  write `VERSION.json` beside `SKILL.md`; install the CLI once on PATH with
  `python -m pip install -e ".[dev]"` — pip, never uv, on both scripts.
  Flags:
  `--dry-run` prints every target path and touches nothing; `--verify`
  exits non-zero unless every target exists and its `SKILL.md` SHA-256
  matches the suite copy. Record suite version and supported contract
  versions separately in `equipment-map-suite/VERSION.json`.
- `tests/test_skill_lint.py`: parse every `SKILL.md`, extract every
  `equipment-map ...` invocation, assert it is in that skill's §9 row and
  carries `--rollout "$ROLLOUT"` where the row has `--rollout`; assert none
  contains `init`, `operator`, `approve`, `unlock`, or `workbench`; assert
  no skill mentions another skill by name; assert the nine headings above
  appear in order and `What you read` contains the sentence quoted above.

## Done when

`pwsh` (PowerShell 7) must be on PATH; if it is not, record `waiting` with
the second command and stop.

```
python -m pytest -q tests/test_skill_lint.py
bash equipment-map-suite/install/install.sh --dry-run
pwsh -NoProfile -File equipment-map-suite/install/install.ps1 -DryRun
```

Lint green; both dry-runs print the same four discovery targets (modulo
home root) and touch nothing.
