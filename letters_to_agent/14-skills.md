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

- `equipment-map-suite/` exactly as the §9 tree. `runtime/equipment-map`
  is a thin launcher for the Python package.
- Each `SKILL.md`: frontmatter `name` and `description` only. Body: role,
  prerequisites, the allowed commands verbatim, how to read exit code and
  `NEXT:`, and the single allowed branch (preflight failure → relay the
  install hint and stop). Stage descriptions name stage number, role, and
  unique task; only `equipment-map-run` is broad.
- `install/install.sh` and `install/install.ps1`: place skills in each
  tool's discovery path (Codex, Claude Code, OpenCode, pi) and put the CLI
  on PATH once. Record suite version and supported contract versions
  separately in `equipment-map-suite/VERSION.json`.
- `tests/test_skill_lint.py`: parse every `SKILL.md`, extract every
  `equipment-map ...` invocation, assert it is in that skill's §9 row;
  assert none contains `init`, `operator`, `approve`, or `unlock`; assert no
  skill mentions another skill by name.

## Done when

```
python -m pytest -q tests/test_skill_lint.py
bash equipment-map-suite/install/install.sh --dry-run
```

Lint green; dry-run prints the target paths for all four tools and
touches nothing.
