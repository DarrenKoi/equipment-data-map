# Equipment Data Map agent contract

This file is read by both maintainer agents and company-local execution agents.
Choose the role from the job the user requested, never from the machine,
network, working directory, or physical location:

- **Maintenance:** follow the sections below when maintaining the architecture
  doc, letters, spec snapshot, skills, and CLI. Do not execute the letters
  unless the user asks.
- **Letter execution:** when asked to execute the letters, follow
  `equipment-data-parser/index.md` as the execution contract, including its
  setup checks and write permissions. The maintainer-only restrictions below
  do not prohibit the execution agent's permitted work.

**During letter execution, read and follow the instructions in
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
  execution agent's problem entries. Keep `spec.md` in sync; the `docs/` copy wins on any difference.
  The company-local hub clone pulls `main` and never pushes; each agent
  model works in a plain copy of it with no git inside, one model at a time
  through the whole sequence, and the engineer copies your updates in
  between sessions (`engineer-guide.md` §1).
- `office/` — the execution agent's ledger (`progress.md`) and problem
  entries. The name is a repository path, not a location check.
  During maintenance, do not create or modify `office/`, or create root-level
  outputs assigned to the execution agent by a build letter. During letter
  execution, the execution agent may create and update files in `office/` and
  root-level build outputs as permitted by `equipment-data-parser/index.md`
  and the current letter, after the required setup checks pass.
  Nothing comes back by git; the user relays sanitized
  summaries, and those are the input for fixing a letter or the spec. The
  execution agent does not edit the letters; the maintainer does.
- `agent_build_steps/` — hands-on course for the maintainer on growing a
  one-file spike into a harness and then an agent (its subject, `spike.py`,
  was removed on 2026-09-22; the course stays as history). Korean, like `docs/`: it is
  read by the user, not by the execution agent. It prescribes no behavior; when
  it disagrees with the spec, the spec wins and the course is wrong.
- `ftp_handler/` — vendored from `skewnono_v3_nuxt`, read-only here. A change
  to it belongs upstream. One change was made here and has been ported to both
  `flask_modules` (upstream) and `skewnono_v3_nuxt` (the other vendored copy):
  `size_dirs` carries a UTC `modified` per file, MDTM beside SIZE, on both
  transports. A later review pass (ValueError caught beside `all_errors`,
  `close()` instead of QUIT, host sanitized in `local_target`, MLSD `type`
  case, constant-time token compare) was ported the same way, as was the
  fixed UTC+09:00 default in `core/client.py`, which replaced a `ZoneInfo`
  lookup that made the package unimportable on Windows without `tzdata`. Covered by `tests/test_sizing_mtime.py` and
  `tests/test_worker_isolation.py` here and by each repo's own suite there.
  The three copies of the changed files are byte-identical,
  so a re-vendor is safe; the standing differences in `ftp_handler/` are this
  repo's `.env` handling of `PROXY_URL`/`PROXY_TOKEN`, which keeps the
  deployment's real host out of the source tree, and `fleet_downloader`
  refusing `FTP_TRANSPORT=direct` on Windows, since the company allows no
  direct FTP from engineer PCs. Both are deliberate and must not be pushed
  upstream. One more change (2026-09-22) is a bug fix that *should* be
  ported: `flask_proxy._unauthorized` treats an empty `FTP_PROXY_TOKEN` as
  no auth, matching the client, so a blank `.env` line no longer makes the
  proxy answer 401 (`tests/test_proxy_token.py`).

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
exercised on pi and the current minimum-model profile the spec names. Codex,
Claude Code and OpenCode are a later extension: each repeats the same scenarios
before it is called supported.
