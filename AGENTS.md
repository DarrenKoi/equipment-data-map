# Equipment Data Map agent contract

This file is read by both maintainer agents and company-local LLM agents on
the office PC. Apply the instructions for the job the user requested:

- **Maintenance:** follow the sections below when maintaining the architecture
  doc, letters, spec snapshot, skills, and CLI. Do not execute the letters
  unless the user asks.
- **Office execution:** when asked to execute the letters, follow
  `equipment-data-parser/index.md` as the execution contract, including its
  setup checks and write permissions. The maintainer-only restrictions below
  do not prohibit the office agent's permitted work.

**During office execution, read and follow the instructions in
`equipment-data-parser/`, and create all results outside that folder. Never
create, modify, or delete files inside `equipment-data-parser/`.** Run commands
from the repository root. Write code, tests, logs, and other results to the
paths specified by the current letter and execution contract, including
`office/` where specified; resolve those paths from the repository root.

Keep `equipment-data-parser/index.md` usable on its own when editing it.
The remaining sections describe repository maintenance.

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
  snapshot of the architecture doc, and `problems.md` is the format of the
  office agent's problem entries. Keep `spec.md` in sync; the `docs/` copy wins on any difference.
  The office PC pulls `main` and never pushes; its commits stay local on
  `main`, ahead of `origin/main` — one local copy per agent model, one
  model at a time through the whole sequence — and merge your updates on
  pull (`engineer-guide.md` §1).
- `office/` — the office agent's ledger (`progress.md`), problem entries and
  `spike.py` workaround. It exists only in the office PC's local copies.
  During maintenance, do not create or modify `office/`, or create root-level
  outputs assigned to the office agent by a build letter. During office
  execution, the office agent may create and update files in `office/` and
  root-level build outputs as permitted by `equipment-data-parser/index.md`
  and the current letter, after the required office setup checks pass.
  Nothing comes back by git; the user relays sanitized
  summaries, and those are the input for fixing a letter or the spec. The
  office agent does not edit the letters; the maintainer does.
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
