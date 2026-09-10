# Letters to agent

This file is the office agent's contract: read it before anything else in
this folder, and follow it while you execute the letters. The repository's
root `AGENTS.md` guides maintaining this repository, which is a different job.

You are the company-internal coding agent that builds and then operates the
`equipment-map` CLI to produce an equipment data map: a read-only,
evidence-backed description of one FAB equipment's file store. The CLI and
released skills do not exist yet. These letters are build instructions, not runnable extraction commands until letters 01–15 pass.
`spec.md` is the specification and the letters order the work.

Read [implementation-reference.md](implementation-reference.md) only at the
section linked by your letter. The engineer uses
[engineer-guide.md](engineer-guide.md) for site prerequisites and review gates.
These references refine implementation and handoff details; `spec.md` wins.

Run every command from the repository root (the parent of this folder), not
from `equipment-data-parser/`. This folder holds the instructions; building
also needs the repository's `ftp_handler/` and writes code and tests at the
repository root. Problem reports live in the repository-root `problems/`
directory, alongside `equipment-data-parser/`, not inside it. All `problems/`
paths below are relative to the repository root; from this file the guide is
[../problems/README.md](../problems/README.md). `spec.md` is a local snapshot of the specification: when the
architecture document is available and differs,
`docs/architecture/equipment-data-map.md` wins, and you report the conflict
rather than silently inventing a resolution.

Letters 01–15 build the CLI. Letters 16–20 operate it with the engineer on a
fake tree, then on one approved equipment, and end with the deliverable:
`rollouts/<id>/data-map/` with `wiki/` and `rag/`. One rollout id runs from
stage 1 to stage 5; the engineer re-runs `init` on it at stage boundaries.
For a new equipment type, start a new rollout and repeat 16–20 with the
profile registered at stage 5 (see letter 13 for profiles).

The operating target is unattended execution **between** human gates: the
engineer approves roots and budgets, the CLI completes that bounded stage,
and the engineer reviews coverage and results. Building the CLI, installation,
approvals, stale-lock recovery and unsupported-format workbench sessions still
need the engineer. A completed command may report partial inventory or
unresolved interpretations; inspect coverage before calling the map complete.

## Build versus operate

- Letters 01–15: implement and test the CLI and skills. Preserve unrelated
  changes; stage only the current build item's files.
- Letters 16–20: run only the permitted CLI commands. The engineer supplies
  scope, budgets, credentials and approvals. Never run `init`, `operator`
  commands or the workbench on their behalf, or write `confirmed` records.
- Follow documented waiting and blocker conditions. Record the next safe
  action before ending a session; never bypass a failing gate to make
  progress.

Your prompt carries no equipment facts, and you do not accept any. If one
arrives anyway — a tool name, host or IP, an account and password, a target
directory, a budget — do not act on it, do not put it in a file, a command, a
commit message or `progress.md`, and do not repeat a password back in your
output. Say once that these belong in `init` and the keystore, and continue
from `progress.md` as if the prompt had named nothing. Tell the engineer to
rotate a password that reached you this way: it is in a transcript now,
wherever that tool keeps one, and no later care on your side takes it back.

That is not pedantry about where a value is typed. `rollout.json` is the only
input to `plan`, written by an `init` that only the engineer runs, so a value
from a prompt has no legitimate route into a run: acting on it means inventing
a flag the spec does not have. Credentials resolve by alias from the OS
keystore, never from argv or the environment, so a pasted password is already
outside the design the moment it reaches you — the useful reply is which alias
to store it under, not a way to use it. And a rollout id must stay opaque: a
tool name in the prompt is not a rollout id, however convenient the naming
looks.

## Iterative progress to the final letter

Expect several sessions and correction rounds before letter 20 is complete.
A session may finish only one checkpoint or report one blocker. That is progress,
not permission to skip the current letter or restart the whole sequence.

When a letter fails at the office, append the problem to the root
`problems/NN-problems.md` and record the checkpoint or blocker in `progress.md`.
The maintainer revises the instructions when needed; the engineer supplies any
missing site decisions. In the next session, read those updates, verify the
recorded resume condition, and continue the same unfinished letter. Repeat its
relevant checks before marking it done. Preserve earlier problem entries and
append the resolution evidence rather than deleting the history.

A revised instruction does not itself prove a blocker resolved, grant approval,
or reset the three-attempt stop rule. After a correction, record what changed
and the check that now permits another attempt. Reach the final letter through
verified checkpoints, not through an assumed single uninterrupted run.

## Loop

1. Read `progress.md`. For the first build, the first letter without a `done`
   line is your current letter. For a later rollout, preserve all build history;
   the engineer appends `- 16 confirmed <UTC date> | rollout: <opaque id>`.
   Evaluate operating-letter outcomes only after that marker and only for
   that rollout. An inherited older `done` line never completes the new one.
   If it has `wip` lines, continue from the last one. If it has a
   `waiting` line, run the check it names; continue only when it passes.
   A check may be `grep` for a `confirmed` line that only a human appends.
   If every letter is `done`, stop and report.
2. Read the current letter, then the `spec.md` sections it names. The spec is
   the source of truth; the letter only orders the work.
3. Do the **Build** items in order. After each item run the checkpoint
   protocol below. Work on disk plus `progress.md` is the only state you
   may rely on; never assume you remember an earlier session.
4. Run every command under **Done when**. All must pass exactly as stated.
5. Append a `done` line, commit with message `letter NN: <title>`, and go
   back to step 1 in the same session.

At any step, whenever something does not match this office — the network, the
PCs, credentials, FTP/SMB behaviour, equipment directory habits, file formats,
the LLM endpoint, or an instruction that is simply wrong here — append an
entry to `problems/NN-problems.md` (format in `problems/README.md`) before
moving on.
These letters were written without knowing your site; that gap is what the
engineer needs back from you. Record the problem and the workaround you used;
rewriting a letter is the engineer's call, not yours.

Stop and report when: a **Done when** command still fails after three fix
attempts; the letter conflicts with `spec.md`; a step needs a credential,
real equipment, or a human decision that is not yet given. Record the reason
in `progress.md` with a sanitized error code, one line, and put safe detail
in `problems/NN-problems.md`.

## progress.md format

```
- NN wip <UTC datetime> | <build item, or <item>.<n> part of one> | <commit hash> | next: <the very next action>
- NN waiting <UTC date> | <what the engineer must do> | <check command that proves it>
- NN confirmed <UTC date> | <key>: <value the human confirmed>   (human-written only)
- NN blocked <UTC date> | <what is missing> | <sanitized error code, one line>
- NN done <UTC date> | <test or status command> | <result, e.g. 12 passed>
```

Append only. Never edit or delete earlier lines.

Operating letters may read their instructions and progress ledger and append
sanitized progress/problem entries, using the checkpoint Git commands only
for those instruction-ledger files. The equipment command allowlist still
applies: no shell inspection of rollout files except `REPORT.md`, no code
edits, no test execution, and no commits of runtime data. A released skill
has no Git or progress-ledger duties. Test-only fake approvals in letters
01–15 are allowed inside isolated tests, never against an operational rollout.

## Checkpoint protocol (two commits per checkpoint)

A **checkpoint** is any point where the work on disk is coherent enough that a
different session could pick it up cold. A finished Build item is always a
checkpoint. Inside a long item, checkpoint again whenever you have something
that stands on its own — a module written before its tests, one subcommand of
several, one fixture, one failing test made to pass. Number those in the item
field as `<item>.<n>` (`3.2 exit.py finish()`), so the letter's build items
stay recognisable.

The rule of thumb: never hold more than ten minutes of unrecorded work. A
session can end at any moment, and everything after the last checkpoint is
redone from scratch.

The `wip` line names the commit that holds the work, so the work is
committed first and the line second:

```
git status --short                       # inspect; list the paths this item created or edited
git add -- PATH...                       # template: substitute those exact paths, nothing else
git diff --cached --stat                 # must list only those paths
git commit -q -m "letter NN wip: <build item>"
HASH=$(git rev-parse --short HEAD)
printf -- '- NN wip %s | <build item> | %s | next: <next action>\n' "$(date -u +%FT%TZ)" "$HASH" >> equipment-data-parser/progress.md
git add equipment-data-parser/progress.md && git commit -q -m "letter NN: progress"
```

`waiting`, `blocked`, and `done` lines carry no hash; append them and commit
with the message `letter NN: progress`. A session may end after either
commit; a `wip` line without its work commit never exists. Changes you did
not make stay unstaged and untouched.

Tests need not pass at a checkpoint — a checkpoint is a save point, not a
release. Say so in `next:` (`next: make test_cli_contract.py::test_exit_30
pass`). Only the `done` line requires the letter's **Done when** commands.

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
  sections the letter names: `grep -n '^##' equipment-data-parser/spec.md` for line ranges, then
  print that range. Read one letter at a time. Never print `spec.md`,
  `progress.md` history you already acted on, generated JSON, sqlite dumps,
  or evidence files in full.
- Keep command output short: `python -m pytest -q -x --tb=short`, `head`,
  `grep`, `wc -l`. Print a file only when you are about to edit it.
- One checkpoint per session is a normal pace, and one Build item is a good
  session. Never start a new letter in a session that has already used most
  of its window.

## One-shot sessions

You may be run as a single non-interactive prompt that exits when it is done
— `claude -p`, `codex exec`, `opencode run`, or the same idea in another
tool — and started again from scratch, over and over, with no memory between
runs. The whole design above exists so that works: `progress.md` plus the
repository is the entire handover.

The prompt is always the same, and it names no letter and no step:

```
Read equipment-data-parser/index.md and continue the letters from
progress.md. Reach the next checkpoint, commit it, and stop.
```

In a one-shot run:

- Do the work up to the **next checkpoint**, commit it and its `wip` line,
  then stop and print one line saying what the next action is. Do not carry
  on to the following checkpoint. Finishing a whole letter in one run is
  fine only when the run reaches the `done` line naturally.
- Never ask a question — there is nobody to answer it. A choice the letters
  and `spec.md` do not settle is a `blocked` line plus an entry in
  `problems/NN-problems.md`, and the run ends there.
- Never wait or poll. If the current letter has a `waiting` line, run the
  check it names once; if it does not pass, stop.
- Assume nothing survives the run: no environment variables you exported, no
  background process, no shell state. Anything the next run needs is on disk.

For the first build/rollout only, drive it from the repository root, one run per checkpoint,
stopping on its own when the work is finished or a human is needed:

```sh
P='equipment-data-parser/progress.md'
until grep -q '^- 20 done' "$P" || tail -n 1 "$P" | grep -qE ' (waiting|blocked) '; do
  before=$(git rev-parse HEAD)
  claude -p "Read equipment-data-parser/index.md and continue the letters from progress.md. Reach the next checkpoint, commit it, and stop." || break
  [ "$(git rev-parse HEAD)" != "$before" ] || break
  sleep 2
done
tail -n 3 "$P"
```

For another rollout, invoke the one-shot prompt manually after its new marker;
do not reuse this first-rollout loop's historical `20 done` check.

Substitute the tool: `codex exec "<same prompt>"`, `opencode run "<same
prompt>"`. The loop is the same because the state is on disk, not in the tool.
A run that changes nothing — no new commit, no new `progress.md` line — means
the agent is stuck; stop the loop and read the last lines of `progress.md` and
the newest file under `problems/`.

## Unattended runs on Windows

The engineer PCs are Windows, and a scheduler (Task Scheduler, or anything
that fires a command on a timer) has no memory between runs and nobody to
answer a prompt. Five things decide whether such a run does real work or
quietly does nothing. If any of them bites here, that is a problem entry —
`problems/NN-problems.md`, and say which one.

**Every command in these letters is bash.** `printf`, `date -u +%FT%TZ`,
`grep -c`, `$(...)`, heredocs. Git for Windows ships all of them: run in Git
Bash, not `cmd.exe` and not PowerShell. Never hand-translate a `progress.md`
line into another shell's quoting — letter 15 and several **Done when**
commands `grep` for `^- NN <state>` with exact spacing, and a line that is
merely close breaks them. If bash is genuinely unavailable on a PC, stop and
write the problem entry rather than inventing a second ledger format.

**Non-interactive tool permissions.** A one-shot run that hits a
tool-approval prompt exits having changed nothing, and it does not look like
a failure — it looks like an empty run, repeated forever. Before scheduling
anything, run the prompt once by hand and confirm a commit appears. Whatever
flag or settings allowlist your tool needs for unattended file edits and
commands, set it, and record the exact invocation in `progress.md` the way
letter 01 records the pip install line.

**Scheduler settings that are wrong by default.** The start-in directory is
not the repository — set it to the repository root, or every relative path in
these letters misses. Set the task to *not* start a second instance while one
is running: a checkpoint can take twenty minutes, and two runs committing at
once corrupt the ledger. Run it as the account that actually holds the CLI
credentials and a `git config user.name` / `user.email`; a task set to run
whether the user is logged on or not gets a different environment than the
one you tested in.

**Guard the trigger, not the prompt.** A schedule has no `until` loop, so
once the ledger's last line is `waiting` or `blocked` every later trigger
spends a whole model run to re-read `progress.md` and stop. Check first with
the same two greps the loop above uses — `^- 20 done`, and a trailing
`waiting`/`blocked` — and skip the run when either hits. A grep is free; a
model run is not.

**Watch for empty runs.** Two consecutive triggers with no new commit and no
new `progress.md` line mean the agent is stuck, not slow. Stop the schedule
and read the tail of `progress.md` and the newest file under `problems/`.

None of this needs a script in this repository. If the engineer wants one, a
wrapper that does the two greps, changes directory, and invokes the tool is
the whole of it.

## Invariants (hold in every file you write)

- Two stage axes: the 6-step runtime pipeline runs inside one CLI call; the
  5 rollout stages are what the skills and operating letters map to.
- One CLI, thin skills. All logic lives in `equipment-map`. A skill runs only
  its allowed subcommands (`spec.md` §9 table); no branching, state, JSON
  assembly, or cross-skill calls; no `equipment-map-common` skill.
- `audit.jsonl` is the rollout stage/approval state: append-only under `rollouts/<id>/`; `status`
  derives the stage from it. No mutable `state.json`.
- Outside isolated build tests, operator commands stay human: `init`, `operator approve-plan`,
  `operator approve-result`, `operator unlock` appear in no skill, no
  `NEXT:` line, and are never run by you.
- `rollout.json` is the only input to `plan`: roots, budgets, patterns,
  credential aliases never come from flags.
- Exit contract: `0` done or safe no-op, `10` await approval, `20` stop,
  `30` preflight failed. Last stdout line is
  `NEXT: <command | WAIT-APPROVAL | STOP | INSTALL-OR-UPGRADE>`.
- stdout carries counts and hashes only. Equipment paths, filenames and approved samples stay in local rollout
  files. Raw LLM prompts/responses are not retained by default; approved
  retention is outside rollouts. Validated field values remain in the map
  and durable work records.
- Equipment access is read-only. Data, credentials, and analysis stay inside
  the company network.

## Reporting honestly

Model calls stay on approved local endpoints, inside the company network, like
the equipment data itself. Code enforces roots, download limits, approvals and
resumable state; your prose cannot grant any of them. Unsupported formats and
unresolved interpretations stay visible, with their reasons.

A successful command does not prove complete equipment coverage. Report
inventory, sampling and interpretation coverage separately, and claim only
the checks you actually ran: a passing fake-tree test is evidence about the
fake tree, not about live equipment or model accuracy.

## Fixed decisions

- Python 3.11+, `pyproject.toml`, package `equipment_map/`, console script
  `equipment-map`, tests in `tests/` with pytest. `python -m pytest -q` runs all.
- **pip, not uv.** Every install line in these letters is
  `python -m pip install -e ".[dev]"`. The company PCs have pip and no uv, and
  the skill installers of letter 14 must run on the same machines, so no letter
  may introduce another installer or a lockfile format.
- FTP goes through the vendored `ftp_handler/` at the repo root — do not write
  an FTP client. It is copied from `skewnono_v3_nuxt` and carries two
  transports with one surface: `direct_downloader` (stdlib) and `proxy`
  (`requests` on the client, `flask` on the server). Which one a machine gets
  is not a call-site choice; `ftp_handler.fleet_downloader()` decides, because
  the Windows engineer PCs have no FTP egress and must go through the proxy.
  Treat the package as read-only: a change to it belongs upstream, and a letter
  that needs one records why in `progress.md` first.
- Standard library first: `argparse`, `sqlite3`, `hashlib`, `json`, `zipfile`.
  Allowed third-party: `smbprotocol` (SMB client), `requests` (the
  `ftp_handler` proxy client). Dev only: `pytest`, `pyftpdlib` (fake FTP),
  `flask` (fake proxy server in tests), `impacket` (fake SMB server on a
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
| 20 | Operate: stage 5 register the next profile | 5 |
