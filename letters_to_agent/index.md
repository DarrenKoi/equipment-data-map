# Letters to agent

You are the agent that builds and then operates the `equipment-map` CLI to
produce an equipment data map: a read-only, evidence-backed description of
one FAB equipment's file store. This folder is self-contained. Everything you
need is here; `spec.md` is the specification and the letters order the work.

Letters 01–15 build the CLI. Letters 16–19 operate it with the engineer on a
fake tree, then on one approved equipment, and end with the deliverable:
`rollouts/<id>/data-map/` with `wiki/` and `rag/`. For a new equipment type,
start a new rollout and repeat 16–19 (see letter 13 for profiles).

## Loop

1. Read `progress.md`. The first letter without a `done` line is your current
   letter. If it has `wip` lines, continue from the last one. If it has a
   `waiting` line, run the check it names; continue only when it passes.
   If every letter is `done`, stop and report.
2. Read the current letter, then the `spec.md` sections it names. The spec is
   the source of truth; the letter only orders the work.
3. Do the **Build** items in order. After each item, append a `wip` line and
   commit. Work on disk plus `progress.md` is the only state you may rely on;
   never assume you remember an earlier session.
4. Run every command under **Done when**. All must pass exactly as stated.
5. Append a `done` line, commit with message `letter NN: <title>`, and go
   back to step 1 in the same session.

Stop and report when: a **Done when** command still fails after three fix
attempts; the letter conflicts with `spec.md`; a step needs a credential,
real equipment, or a human decision that is not yet given. Record the reason
in `progress.md` with the exact failing output, one line.

## progress.md format

```
- NN wip <UTC datetime> | <build item finished> | <commit hash> | next: <the very next action>
- NN waiting <UTC date> | <what the engineer must do> | <check command that proves it>
- NN blocked <UTC date> | <what is missing> | <failing output, one line>
- NN done <UTC date> | <test or status command> | <result, e.g. 12 passed>
```

Append only. Never edit or delete earlier lines.

## Context budget

Your context window is finite and will fill during long letters. Treat it as
disposable: disk plus `progress.md` is the state, your memory is not.

- Session end is always safe after a `wip` line and a commit. When the
  harness warns that context is nearly full, or you have finished a Build
  item and the window is more than about two-thirds used, finish that item,
  append `wip` with `next:`, commit, and end the session with one sentence:
  "Restart with the same command." The next session resumes from the
  `next:` field. Ending early costs nothing; a half-written item with no
  `wip` line costs a whole redo.
- Read only what the current step needs. From `spec.md` read only the
  sections the letter names: `grep -n '^##' spec.md` for line ranges, then
  print that range. Read one letter at a time. Never print `spec.md`,
  `progress.md` history you already acted on, generated JSON, sqlite dumps,
  or evidence files in full.
- Keep command output short: `python -m pytest -q -x --tb=short`, `head`,
  `grep`, `wc -l`. Print a file only when you are about to edit it.
- One Build item per session is a normal pace. Never start a new letter in
  a session that has already used most of its window.

## Invariants (hold in every file you write)

- Two stage axes: the 6-step runtime pipeline runs inside one CLI call; the
  5 rollout stages are what the skills and operating letters map to.
- One CLI, thin skills. All logic lives in `equipment-map`. A skill runs only
  its allowed subcommands (`spec.md` §9 table); no branching, state, JSON
  assembly, or cross-skill calls; no `equipment-map-common` skill.
- `audit.jsonl` is the state: append-only under `rollouts/<id>/`; `status`
  derives the stage from it. No mutable `state.json`.
- Operator commands stay human: `init`, `operator approve-plan`,
  `operator approve-result`, `operator unlock` appear in no skill, no
  `NEXT:` line, and are never run by you.
- `rollout.json` is the only input to `plan`: roots, budgets, patterns,
  credential aliases never come from flags.
- Exit contract: `0` done or safe no-op, `10` await approval, `20` stop,
  `30` preflight failed. Last stdout line is
  `NEXT: <command | WAIT-APPROVAL | STOP | INSTALL-OR-UPGRADE>`.
- stdout carries counts and hashes only. Paths, filenames, sample content,
  credentials, prompts and responses go to files under the rollout directory.
- Equipment access is read-only. Data, credentials, and analysis stay inside
  the company network.

## Fixed decisions

- Python 3.11+, `pyproject.toml`, package `equipment_map/`, console script
  `equipment-map`, tests in `tests/` with pytest. `python -m pytest -q` runs all.
- Standard library first: `argparse`, `ftplib`, `sqlite3`, `hashlib`, `json`,
  `zipfile`. Allowed third-party: `smbprotocol` (SMB client). Dev only:
  `pytest`, `pyftpdlib` (fake FTP), `impacket` (fake SMB server on a
  non-standard port). Add nothing else without recording why in `progress.md`.
- Every CLI exit goes through one function that prints the final `NEXT:` line
  and returns the exit code. No other code prints `NEXT:`.
- Every timestamp on disk is UTC ISO-8601. Every hash is SHA-256 hex.
- Test fixtures never contain real equipment addresses, paths, or credentials.
- Code, comments, and commit messages are English.

## Letters

| NN | Title | Rollout stage |
|---|---|---|
| 01 | CLI skeleton and exit contract | all |
| 02 | Rollout state, plan, approvals, lock | all |
| 03 | Source interface, FTP adapter, fake FTP | 1 |
| 04 | SMB adapter, fake SMB | 1 |
| 05 | Inventory with checkpoints and budgets | 1 |
| 06 | Grouping into file families | 1 |
| 07 | Sampling with budgets and dedup | 1 |
| 08 | Deterministic extraction | 1 |
| 09 | Data map output and stage 1 `next` | 1 |
| 10 | Stage 1 verification scenarios | 1 |
| 11 | Local LLM analysis and stage 2 `next` | 2 |
| 12 | Wiki and RAG generation, stage 4 `next` | 4 |
| 13 | Equipment profiles, access window, stage 3 and 5 | 3, 5 |
| 14 | Skill suite and installers | all |
| 15 | Cross-tool scenario validation | all |
| 16 | Operate: stage 1 on the fake tree | 1 |
| 17 | Operate: stage 2 with the local LLM | 2 |
| 18 | Operate: stage 3 pilot on one equipment | 3 |
| 19 | Operate: stage 4 publish, the deliverable | 4 |
