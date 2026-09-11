# Equipment Data Map agent contract

This contract is for agents **maintaining** this repository: the architecture
doc, the letters, the spec snapshot, the skills, and the CLI once it exists.

Executing the letters is a different job with its own contract,
`equipment-data-parser/index.md`. Do not start executing them unless the user
asks. When you change them, keep that file usable on its own — the office
agent must never need to read this one.

## Purpose

Build a company-internal exploration kit that lets an LLM inspect one FAB
equipment file store thoroughly and safely. The deliverable is not just a
collector: it is the guide, portable skills, safe scripts, checkpoints, review
sheets, and evaluation cases an engineer needs to supervise a long-running
exploration.

## Read first

`docs/architecture/equipment-data-map.md` is the source of truth for the
runtime pipeline, the five rollout stages, the safeguards, and the model
validation profile. Read it before changing architecture, skills, collection
or extraction behavior, checkpoints, approval gates, or evaluation criteria —
and do not restate it here. A rule that lives in two places drifts: this file
says where things are and what wins, the doc says what the system does.

Language is fixed per kind of file. Agent-facing files — `AGENTS.md`,
`CLAUDE.md`, every `SKILL.md`, and everything under `equipment-data-parser/` —
are English, as are code, comments, and commit messages. Design docs under
`docs/` are Korean. Write in the language the file already uses; do not
translate one into the other.

## Where the pieces are

- `docs/architecture/equipment-data-map.md` — the spec, in Korean. It wins.
- `equipment-data-parser/` — the ordered build-and-operate sequence for the
  company LLM. `index.md` is its contract and entry point, `spec.md` is a
  snapshot of the architecture doc, `progress.md` is the append-only state
  ledger. Keep `spec.md` in sync; the `docs/` copy wins on any difference.
- `problems/` — where the office agent reports what the
  letters got wrong about its site, one `NN-problems.md` per letter. Those
  entries are the input for fixing a letter or the spec. That agent does not
  edit the letters; you do.
- `agent_build_steps/` — hands-on course for the maintainer on growing
  `spike.py` into a harness and then an agent. Korean, like `docs/`: it is
  read by the user, not by the office agent. It prescribes no behavior; when
  it disagrees with the spec, the spec wins and the course is wrong.
- `ftp_handler/` — vendored from `skewnono_v3_nuxt`, read-only here. A change
  to it belongs upstream. One change was made here and has been ported to both
  `flask_modules` (upstream) and `skewnono_v3_nuxt` (the other vendored copy):
  `size_dirs` carries a UTC `modified` per file, MDTM beside SIZE, on both
  transports. A later review pass (ValueError caught beside `all_errors`,
  `close()` instead of QUIT, host sanitized in `local_target`, MLSD `type`
  case, constant-time token compare) was ported the same way. Covered by `tests/test_sizing_mtime.py` and
  `tests/test_worker_isolation.py` here and by each repo's own suite there.
  The three copies of the changed files are byte-identical,
  so a re-vendor is safe; the only standing difference in `ftp_handler/` is this
  repo's `.env` handling of `PROXY_URL`/`PROXY_TOKEN`, which is deliberate and
  must not be pushed upstream — it is what keeps the deployment's real host out
  of the source tree.

## Skill deliverables

- Publish portable Agent Skills usable from Codex, Claude Code, OpenCode, and
  pi through the company Skill Market.
- Keep each stage skill narrow: goal, prerequisites, permitted commands,
  checkpoint, review sheet, stop conditions, and completion evidence.
- Keep state and safety decisions in scripts rather than model prose. Skills
  guide the model; scripts make unsafe or invalid transitions fail closed.
- Keep tool-specific installation metadata outside the shared skill body
  unless the target platform requires it.

## Completion evidence

A change is complete only when its smallest relevant scenario proves the
behavior. Prefer fake FTP trees and copied samples before any approved
equipment trial. Verify read-only access, budget stops, checkpoint resume,
unreadable-file retention, evidence traceability, and rejection of invalid
stage transitions. A skill release also needs the same task scenario
exercised across the four supported agent tools and the current minimum-model
profile the spec names.
