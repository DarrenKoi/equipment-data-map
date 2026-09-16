# Letters to agent

This file is the letter-execution contract: read it before anything else in
this folder when the user asks you to execute the letters. Use the requested
job, not your machine, network, working directory, or physical location, to
choose this role. The repository's root `AGENTS.md` guides maintenance, which
is a different job.

**The current sequence starts at letter 01.** Letter 00 is retired after
repeated successful runs. Do not execute it or wait on its historical
`00 discovery` or `00 done` entries. Read `office/progress.md` and select the
first unfinished letter from the table at the bottom of this file; a new model
folder therefore starts at 01.

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
repository root. Your ledger and problem reports live in the repository-root
`office/` folder; the problem entry format is [problems.md](problems.md). `spec.md` is a local snapshot of the specification: when the
architecture document is available and differs,
`docs/architecture/equipment-data-map.md` wins, and you report the conflict
rather than silently inventing a resolution.

Letters 01–15 build the CLI. Letters 16–20 operate it with the engineer on a
fake tree, then on one approved equipment, and end with the deliverable:
`rollouts/<id>/data-map/` with `wiki/`, `graph/` and `rag/`. One rollout id runs from
stage 1 to stage 5; the engineer re-runs `init` on it at stage boundaries.
For a new equipment type, start a new rollout and repeat 16–20 with the
profile registered at stage 5 (see letter 13 for profiles).

The operating target is unattended execution **between** human gates: the
engineer approves roots and budgets, the CLI completes that bounded stage,
and the engineer reviews coverage and results. Building the CLI, installation,
approvals, stale-lock recovery and unsupported-format workbench sessions still
need the engineer. A completed command may report partial inventory or
unresolved interpretations; inspect coverage before calling the map complete.

## Your folder and the `office/` folder

Your working directory is a plain copy of the repository with no git in it;
never run git here. The whole sequence runs in this one copy
([engineer-guide.md](engineer-guide.md) §1); another model gets another copy
only after this one is finished. Inside it you may work on several letters at
once through subagents you start yourself — see **Parallel jobs** — but there
is only ever one copy and one ledger. Your working directory is your whole
identity: never read or write in another copy, and never take a model name
from the prompt. The maintainer's updates arrive only when the engineer
copies them in between sessions.

Before any other step, `office/progress.md` must exist in the working
directory. When it does not, print one line asking the engineer to run the
execution-workspace setup, and stop without writing.

Write only in `office/`: `office/progress.md` and
`office/problems/NN-problems.md`. Historical `office/spike.py`,
`equipment.toml`, and `out/` files may remain on this PC, but the active
sequence does not run or change them. The build letters permit their specified
new files at the repository root.
Everything else in the
repository — this folder, `spike.py`, `ftp_handler/`, the maintainer tests — is
the maintainer's: read it, and report what is wrong here in a problem entry.
The maintainer never writes in `office/`, so updates leave it untouched.

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
`office/progress.md`, and do not repeat a password back in your
output. Say once that these belong in `init` and the keystore, and continue
from `office/progress.md` as if the prompt had named nothing. Tell the engineer to
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

When a letter fails in the execution workspace, append the problem to the root
`office/problems/NN-problems.md` and record the checkpoint or blocker in `office/progress.md`.
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

The active progression starts at letter 01. Historical letter 00 records do
not gate it.

1. Read `office/progress.md`. For the first build, the first letter without a `done`
   line is your current letter — "letter" meaning a row in the table at the
   bottom of this file, so a number with no row (04) is skipped, never waited on. For a later rollout, preserve all build history;
   the engineer appends `- 16 confirmed <UTC date> | rollout: <opaque id>`.
   Evaluate operating-letter outcomes only after that marker and only for
   that rollout. An inherited older `done` line never completes the new one.
   If it has `wip` lines, continue each unfinished letter from that letter's
   own last `wip` line. If it has a
   `waiting` line, run the check it names; continue only when it passes.
   A check may be `grep` for a `confirmed` line that only a human appends.
   If every letter is `done`, stop and report.

   A `done` line carries the hash of the letter file it finished, so re-check
   them before you choose. A letter whose file no longer matches its hash, or
   whose `done` line has no `letter:` field, was revised after you finished
   it and is not done:

   ```sh
   awk -F'letter: ' '/^- [0-9][0-9] done /{split($0,a," "); h[a[2]]=(NF>1?$2:"none")} END{for (n in h) print n, h[n]}' office/progress.md | sort | while read -r n h; do f=$(ls equipment-data-parser/$n-*.md 2>/dev/null); [ -n "$f" ] && [ "$(sha256sum "$f" | cut -c1-12)" = "$h" ] || echo "redo $n"; done
   ```

   Finish an open `wip` or `waiting` letter first; after that the earliest
   `redo` letter is your current letter, ahead of the first letter with no
   `done` line. Redoing means reconciling what is already on disk with the
   letter's current text and running its **Done when** again — keep what
   still passes, and never rebuild a module from scratch to satisfy an
   addition. Nobody has to tell you a letter changed; this check is how you
   find out. For letters 16–20 a stage already run against equipment is not
   re-run: record the revision in `office/problems/NN-problems.md`, append
   `waiting`, and let the engineer decide.

   When more than one letter is ready at once, see **Parallel jobs** below.
2. Read the current letter, then the `spec.md` sections it names. The spec is
   the source of truth; the letter only orders the work.
3. Do the **Build** items in order. After each item run the checkpoint
   protocol below. Work on disk plus `office/progress.md` is the only state you
   may rely on; never assume you remember an earlier session.
4. Run every command under **Done when**. All must pass exactly as stated.
5. Append a `done` line and go back to step 1 in the same session.

At any step, whenever something does not match the available environment or
resources — the network, system image, credentials, FTP behaviour, equipment
directory habits, file formats, the LLM endpoint, or an instruction that is
simply wrong here — append an
entry to `office/problems/NN-problems.md` (format in
`equipment-data-parser/problems.md`) before
moving on.
These letters were written without knowing your site; that gap is what the
engineer needs back from you. Record the problem and the workaround you used;
rewriting a letter is the engineer's call, not yours.

Stop and report when: a **Done when** command still fails after three fix
attempts; the letter conflicts with `spec.md`; a step needs a credential,
real equipment, or a human decision that is not yet given. Record the reason
in `office/progress.md` with a sanitized error code, one line, and put safe detail
in `office/problems/NN-problems.md`.

## Parallel jobs

Letters that need different files may run at the same time. You are the
coordinator: you choose the ready letters, start one subagent per letter, and
stay the only writer of `office/progress.md`.

1. A letter is ready when every letter in its **Needs** column has a current
   `done` line. Start at most three at once.
2. One subagent per letter, never two inside one letter: a letter is the
   smallest unit that has a **Done when**.
3. Append one `wip` line per letter before the batch starts, so a session that
   dies leaves the batch visible to the next one. Give each subagent its letter
   number, the files that letter names, and nothing else to do. A subagent
   writes no ledger line and starts no subagent of its own.
4. A job writes only the files its letter names, plus its own test module.
   `equipment_map/cli.py` and `pyproject.toml` belong to letter 01; letters 03
   and 08 also edit `cli.py`, so those two never share a batch.
   Every job runs in this same folder. There is no git here, so there is no
   worktree, branch or clone to isolate a job in; file ownership is the whole
   of the isolation, which is why the rule above is the one that matters.
5. When the batch is in, run every finished letter's **Done when** again,
   together, in the shared tree. Those runs earn the `done` lines: a letter
   that passed inside its own job proves nothing about the package. Fix a
   failure here yourself, one letter at a time, before the next batch.
6. If two jobs edited the same file, leave both `wip` and redo them one after
   the other.

Letters 16–20 never share a batch: each waits on the previous stage's human
approval, and one rollout has one state. Running letters one at a time is
always allowed and never wrong — fan out when the **Needs** column says you
can, not because a letter looks long.

## office/progress.md format

```
- NN wip <UTC datetime> | <build item, or <item>.<n> part of one> | next: <the very next action>
- NN waiting <UTC date> | <what the engineer must do> | <check command that proves it>
- NN confirmed <UTC date> | <key>: <value the human confirmed>   (human-written only)
- NN blocked <UTC date> | <what is missing> | <sanitized error code, one line>
- NN done <UTC date> | <test or status command> | <result, e.g. 12 passed> | letter: <first 12 hex of sha256 of that letter file>
```

Append only. Never edit or delete earlier lines.

Operating letters may read their instructions and progress ledger and append
sanitized progress/problem entries, and nothing else. The equipment command allowlist still
applies: no shell inspection of rollout files except `REPORT.md`, no code
edits, and no test execution. A released skill
has no progress-ledger duties. Test-only fake approvals in letters
01–15 are allowed inside isolated tests, never against an operational rollout.

## Checkpoint protocol (one ledger line per Build item)

A **checkpoint** is a finished Build item: the work on disk is coherent enough
that a different session could pick it up cold. Checkpoint at the end of each
Build item, not inside it. If a single item runs long enough that stopping
would lose serious work — a module plus its tests, several subcommands —
checkpoint mid-item and name the part in the item field (`3.2 exit.py`), but
that is the exception, not the routine.

The work stays on disk and the ledger line records it:

```
printf -- '- NN wip %s | <build item> | next: <next action>\n' "$(date -u +%FT%TZ)" \
  >> office/progress.md
tail -n 1 office/progress.md             # must be the line you just appended
```

`waiting` and `blocked` lines follow the same shape. A `done` line adds the
hash of the letter you finished:

```sh
printf -- '- NN done %s | <command> | <result> | letter: %s\n' "$(date -u +%F)" \
  "$(sha256sum equipment-data-parser/NN-*.md | cut -c1-12)" >> office/progress.md
```

Files you did not make stay untouched.

Tests need not pass at a checkpoint — a checkpoint is a save point, not a
release. Say so in `next:` (`next: make test_cli_contract.py::test_exit_30
pass`). Only the `done` line requires the letter's **Done when** commands.

## Context budget

Your context window is finite and will fill during long letters. Treat it as
disposable: disk plus `office/progress.md` is the state, your memory is not.

- Session end is always safe after a checkpoint line. Keep going while the
  window allows it, and finish the letter in one session when you can. When
  the harness warns that context is nearly full, finish the current Build
  item, append `wip` with `next:`, and end the session with one
  sentence: "Restart with the same command." The next session resumes from
  the `next:` field. A half-written item with no `wip` line costs a whole
  redo — that is the only thing worth stopping early to avoid.
- Read only what the current step needs. From `spec.md` read only the
  sections the letter names: `grep -n '^##' equipment-data-parser/spec.md` for line ranges, then
  print that range. Read one letter at a time. Never print `spec.md`,
  `office/progress.md` history you already acted on, generated JSON, sqlite dumps,
  or evidence files in full.
- Keep command output short: `python -m pytest -q -x --tb=short`, `head`,
  `grep`, `wc -l`. Print a file only when you are about to edit it.
- A whole letter in a session is a good session; several short ones is
  better. Context, not procedure, decides when to stop. Do not start a new
  letter in a session that has already used most of its window.

## One-shot sessions

You may be run as a single non-interactive prompt that exits when it is done
— `claude -p`, `codex exec`, `opencode run`, or the same idea in another
tool — and started again from scratch, over and over, with no memory between
runs. The whole design above exists so that works: `office/progress.md` plus the
repository is the entire handover.

The prompt is always the same, and it names no letter and no step:

```
Read equipment-data-parser/index.md and continue the letters from
office/progress.md. Reach the next checkpoint, record it, and stop.
```

In a one-shot run:

- Work through as many checkpoints as the context window allows, recording
  each, and prefer finishing the whole letter. Stop at a checkpoint when the
  window is nearly full, or at a `waiting`/`blocked` line, and print one line
  saying what the next action is.
- Never ask a question — there is nobody to answer it. A choice the letters
  and `spec.md` do not settle is a `blocked` line plus an entry in
  `office/problems/NN-problems.md`, and the run ends there.
- Never wait or poll. If the current letter has a `waiting` line, run the
  check it names once; if it does not pass, stop.
- Assume nothing survives the run: no environment variables you exported, no
  background process, no shell state. Anything the next run needs is on disk.

The repeated-run loop and scheduler below apply to the active letters 01–20.
Historical letter 00 records do not block them.

For the first build/rollout only, drive it from the repository root, one run per checkpoint,
stopping on its own when the work is finished or a human is needed:

```sh
P='office/progress.md'
until grep -q '^- 20 done' "$P" || tail -n 1 "$P" | grep -qE ' (waiting|blocked) '; do
  before=$(wc -l < "$P")
  claude -p "Read equipment-data-parser/index.md and continue the letters from office/progress.md. Reach the next checkpoint, record it, and stop." || break
  [ "$(wc -l < "$P")" != "$before" ] || break
  sleep 2
done
tail -n 3 "$P"
```

For another rollout, invoke the one-shot prompt manually after its new marker;
do not reuse this first-rollout loop's historical `20 done` check.

Substitute the tool: `codex exec "<same prompt>"`, `opencode run "<same
prompt>"`. The loop is the same because the state is on disk, not in the tool.
A run that changes nothing — no new `office/progress.md` line — means
the agent is stuck; stop the loop and read the last lines of `office/progress.md` and
the newest file under `office/problems/`.

## Unattended runs on Windows

The engineer PCs are Windows, and a scheduler (Task Scheduler, or anything
that fires a command on a timer) has no memory between runs and nobody to
answer a prompt. Five things decide whether such a run does real work or
quietly does nothing. If any of them bites here, that is a problem entry —
`office/problems/NN-problems.md`, and say which one.

**Every command in these letters is bash.** `printf`, `date -u +%FT%TZ`,
`grep -c`, `$(...)`, heredocs. Git for Windows ships all of them: run in Git
Bash, not `cmd.exe` and not PowerShell. Never hand-translate a `office/progress.md`
line into another shell's quoting — letter 15 and several **Done when**
commands `grep` for `^- NN <state>` with exact spacing, and a line that is
merely close breaks them. If bash is genuinely unavailable on a PC, stop and
write the problem entry rather than inventing a second ledger format.

**Non-interactive tool permissions.** A one-shot run that hits a
tool-approval prompt exits having changed nothing, and it does not look like
a failure — it looks like an empty run, repeated forever. Before scheduling
anything, run the prompt once by hand and confirm a new `office/progress.md` line appears. Whatever
flag or settings allowlist your tool needs for unattended file edits and
commands, set it, and record the exact invocation in `office/progress.md` the way
letter 01 records the pip install line.

**Scheduler settings that are wrong by default.** The start-in directory is
not the repository — set it to the repository root (that model's folder), or
every relative path in these letters misses. Set the task to *not* start a second instance while one
is running: a checkpoint can take twenty minutes, and two runs appending at
once corrupt the ledger. Run it as the account that actually holds the CLI
credentials; a task set to run
whether the user is logged on or not gets a different environment than the
one you tested in.

**Guard the trigger, not the prompt.** A schedule has no `until` loop, so
once the ledger's last line is `waiting` or `blocked` every later trigger
spends a whole model run to re-read `office/progress.md` and stop. Check first with
the same two greps the loop above uses — `^- 20 done`, and a trailing
`waiting`/`blocked` — and skip the run when either hits. A grep is free; a
model run is not.

**Watch for empty runs.** Two consecutive triggers with no
new `office/progress.md` line mean the agent is stuck, not slow. Stop the schedule
and read the tail of `office/progress.md` and the newest file under `office/problems/`.

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
  is not a call-site choice; `ftp_handler.fleet_downloader()` decides. The
  operating machine is a Windows engineer PC with no FTP egress, so **proxy is
  the path that must work**; direct is the development convenience, and a
  feature that works only on direct is not done. `fleet_downloader` refuses
  `FTP_TRANSPORT=direct` on Windows; never work around that.
  Metadata comes from `size_dirs` — path, size and UTC mtime in one connection,
  on both transports — never from `list_dirs`, which carries paths only.
  The package is otherwise read-only: a change to it belongs upstream in
  `skewnono_v3_nuxt`, and a letter that needs one records why in `office/progress.md`
  first. One change has already been made here and ported upstream — `size_dirs`
  carries a UTC `modified` per file, MDTM alongside SIZE, on both transports.
  Do not re-derive it, and do not treat it as licence for another.
- Standard library first: `argparse`, `sqlite3`, `hashlib`, `json`, `zipfile`.
  Allowed third-party: `requests` (the `ftp_handler` proxy client) only. Dev
  only: `pytest`, `pyftpdlib` (fake FTP), `flask` (fake proxy server in
  tests). Add nothing else without recording why in `office/progress.md`.
- Every CLI exit goes through one function that prints the final `NEXT:` line
  and returns the exit code. No other code prints `NEXT:`.
- Every timestamp on disk is UTC ISO-8601. Every hash is SHA-256 hex.
- Test fixtures never contain real equipment addresses, paths, or credentials.
- Code and comments are English.

## Letters

`Needs` is what must carry a current `done` line before that letter starts.
Letters with disjoint needs and disjoint files are the ones **Parallel jobs**
lets you batch.

| NN | Title | Rollout stage | Needs |
|---|---|---|---|
| 01 | CLI skeleton and exit contract | all | — |
| 02 | Rollout state, plan, approvals, lock | all | 01 |
| 03 | Source interface, FTP adapter, fake FTP | 1 | 01 |
| 05 | Inventory with checkpoints and budgets | 1 | 02, 03 |
| 06 | Grouping into file families | 1 | 05 |
| 07 | Sampling with budgets and dedup | 1 | 03, 06 |
| 08 | Deterministic extraction | 1 | 07 |
| 09 | Data map output and stage 1 `next` | 1 | 05, 06, 07, 08 |
| 10 | Stage 1 verification scenarios | 1 | 09 |
| 11 | Local LLM analysis and stage 2 `next` | 2 | 02, 09 |
| 12 | Wiki, Graph and RAG generation, stage 4 `next` | 4 | 09, 11 |
| 13 | Equipment profiles, access window, stage 3 and 5 | 3, 5 | 09, 11 |
| 14 | Skill suite and installers | all | 01 |
| 15 | Cross-tool scenario validation | all | 02, 11, 14 |
| 16 | Operate: stage 1 on the fake tree | 1 | 01–15 |
| 17 | Operate: stage 2 with the local LLM | 2 | 16 |
| 18 | Operate: stage 3 pilot on one equipment | 3 | 17 |
| 19 | Operate: stage 4 publish, the deliverable | 4 | 18 |
| 20 | Operate: stage 5 register the next profile | 5 | 19 |

Letter 04 was SMB. There is no SMB at this site yet, so it was removed rather
than built ahead of a need; number 04 stays vacant so every later letter keeps
the number `office/progress.md` already refers to. Adding SMB later means a new letter
behind the same `Source` interface, not a renumbering.
