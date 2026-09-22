# Engineer handoff

This file is for the supervising engineer. The office agent starts at
[index.md](index.md). These are instructions for a CLI to be built, not a claim
that it is installed or ready. Do not run the operating commands below until
letters 01–15 and their gates pass. Keep filled site information local and
untracked; this repository contains blank guidance and synthetic examples only.

## 1. Before the first office session

Prepare one company PC, a company-approved local model connection for the agent,
Python 3.11+, Git Bash on Windows, and pip access to approved packages. Check the repository root is the task's working directory. Use one
running agent instance. Verify permissions with one supervised build checkpoint
before scheduling it; do not grant blanket approval to equipment operations.

The initial repository contains the vendor FTP package and five transport tests.
There is no `equipment-map` CLI, extraction suite or released skill suite yet.
The separate metadata and execution-lifecycle gaps in implementation-reference.md
§4 need upstream/deployment verification. File-size capping is not a prerequisite:
use normal downloads, including eligible large/unknown-size files, with actual-byte
accounting and best-effort targets. No cap workaround is required. Mock tests
can guide implementation but cannot waive that blocker.

Letter 00 has completed repeated office validation and is retired. Start the
active sequence at letter 01. Keep its `spike.py`, `equipment.toml`, and `out/`
artifacts only as local diagnostic fallback until letter 18 proves the formal
CLI on one real equipment; do not rerun or modify them in the active sequence.

### The hub clone and the model folders

The office PC holds one git clone, the hub: it tracks the maintainer's
remote, stays on `main`, only ever pulls, and no agent runs in it. Give this
PC read-only access to the remote so a push fails. The agent never uses git.
It writes in `office/` (ledger, problem entries, a changed `office/spike.py`)
plus the new files the build letters create, as plain files. Findings travel
home by hand: relay a sanitized summary of `office/problems/` and the
`office/progress.md` result to the maintainer, with no equipment addresses,
paths or credentials.

**One model takes the whole sequence.** One approved model runs letters 01
through 20 to the end. It is always the agent model and, once interpretation is
enabled, is also the approved internal interpretation model before any other model is tried. Do not switch models
mid-sequence: a half-built CLI or a half-interpreted map from two models cannot
be reviewed as one result. Comparing models is a later exercise, on a finished
process.

How the agent tool splits work across subagents is its own business; the
letters do not prescribe it. If you install `pi-subagents` in the model
folder's pi (`pi install npm:pi-subagents`, then `pi list` to confirm), one
thing still has to hold: builtin roles inherit the parent session's model,
so confirm on this PC that no `subagents.defaultModel` and no
`subagents.agentOverrides.worker.model` is set in
`~/.pi/agent/settings.json` or the project settings, or pin it with
`"worker": {"model": "inherit"}`. A child on another model breaks the rule
above silently, in files the parent then reports as done. Do not use the
worktree isolation the extension documents — there is no git in the model
folder to make a worktree from. Two agent sessions in one folder, or the same
letters in two folders, produce a build nobody can review — that is still
out.

**One hub, one folder per model.** The model that runs the letters gets its
own plain copy of the hub, `<repo>-<model>/`, with no `.git` inside. When a
later model is tried it gets a fresh copy, so the two never share a ledger,
an `office/spike.py`, root build outputs, `out/` or `rollouts/`.
The working directory is the whole identity: the prompt never names the
model, and an agent launched in `<repo>-<model>/` is that model's run. The
first line of that folder's `office/progress.md` names the agent model, and
the rollout configuration names the internal interpretation model. `<model>` is a short
slug of letters, digits and dashes (`qwen3-8b`), never a host, path or
credential. A `.venv` made inside the model folder stays there; git ignores
it and the copies below never touch it.

Set each up once, in Git Bash at the hub's root, with a clean tree on `main`.
A file-manager copy that leaves out `.git` and `out/` is the same thing.

```sh
M=qwen3-8b                                            # the model slug for this folder
D="../$(basename "$PWD")-$M"
(
  set -e
  test "$(git branch --show-current)" = main
  test -z "$(git status --porcelain)"
  git pull --ff-only
  cp -r . "$D"                                        # .env and equipment.toml travel with it
  rm -rf "$D/.git" "$D/out"                           # no git in the model folder, no stale results
  mkdir -p "$D/office/problems"
  printf '# Progress\n\nModel: %s. Append-only. Format is in equipment-data-parser/index.md.\n' "$M" > "$D/office/progress.md"
)
```

The same script restarts a model from scratch: first delete everything in
its folder except `.venv`, `.env` and `equipment.toml`, then run it again.
`engineer.toml` goes too: its confirmations belong to the discarded build.

Only the agent writes `office/progress.md`; never add a line to it. When the
agent needs an answer from you — skill discovery roots (letter 14), the
validation result (letter 15), the rollout to operate, an extractor release
— its `waiting` line says so and you write it in `engineer.toml` at the model
folder's root. Copy `engineer.toml.example` there once; each table in it
names the letter that reads it. Editing the file is what clears such a
`waiting` line. It holds no host, remote path, budget or credential: those
go to `init` and the keystore.

`python tools/reset_model_folder.py --reset` from the hub (folder and slug are
set at the top of the file; two arguments after the flag override them) does
both the first setup and a restart in one step. Without `--reset` the script
refreshes instead, which is the between-sessions move below.

Leave the historical `equipment.toml` untouched. Supply internal interpretation
settings only when the current letter requests them, through the engineer-run
`init` flow.
Launch that model's agent tool, one-shot loop or scheduled task with the
model folder as the working directory; the letters say "repository root" and
mean that directory.

Bring maintainer updates over between agent sessions: disable the schedule
first and let the running agent and its child processes finish. Pull once in
the hub, then copy the tracked files into the active model folder. There is
no merge: the maintainer never writes in `office/`, `.env`,
`equipment.toml`, `engineer.toml`, `out/`, `.venv/` or the root build outputs, so every
tracked file can simply be replaced by the hub's copy.

```sh
D=../equipment-data-map-qwen3-8b                      # the active model folder
git pull --ff-only                                    # in the hub, on main
python tools/reset_model_folder.py "$D"
```

Refreshing is the script's default: it replaces the tracked files and deletes
nothing else, so `office/`, the built CLI, its tests, `equipment-map-suite/`
and `rollouts/` survive. It prints the tracked files that changed, removes a
letter the hub no longer ships, and names the changed letters that
`office/progress.md` already marks `done`.

You do not have to pass that list on. Each `done` line carries the hash of the
letter it finished, so the next session re-checks them, finds the revised ones
itself and redoes them before moving on (index.md, Loop step 1). The printed
list only tells you how much work that will be. A hand copy or file-manager
copy is detected the same way. When the update changed `spike.py` and
`office/spike.py` exists, compare them in the model folder
(`diff spike.py office/spike.py`): delete the copy if the maintainer's
version covers the workaround, otherwise port the new changes into it. Run
the home checks in the model folder before restarting the schedule.

### Before an overnight run

An unattended run has nobody to answer a prompt and no memory between runs.
Everything it will need must be in place before you leave; a run that meets
a missing piece stops in its first minute and the night is spent. Go through
this list, in order, in Git Bash at the model folder's root:

1. **Prove one run by hand.** Run the one-shot prompt from index.md
   ("One-shot sessions") once, non-interactively, and confirm
   `office/progress.md` grew by a line. A run that hits a tool-approval
   prompt exits having changed nothing, and it does not look like a failure —
   it looks like an empty run, repeated all night. Whatever flag or settings
   allowlist your tool needs for unattended file edits and commands, set it
   now and keep the exact invocation in your local notes; grant no blanket
   approval to equipment operations.
2. **Answer `engineer.toml` for everything the night can ask**: the
   `[rollout]` or `[release]` table, letter 14's discovery roots. An
   unanswered question is a `waiting` line, and the loop stops there. Letter
   15's confirmation and every operating gate need your review, so a night
   that reaches one ends there; that is expected.
3. **If the night can reach letters 16–17**, start the fixture server in its
   own terminal (§2, `python -m tests.fixtures.serve`) and run `init` (§3).
   The agent starts no server and runs no `init`.
4. **Bring maintainer updates over first**, never during the run (above).
5. **Start the loop and leave the window open.** The `until` loop in
   index.md's "One-shot sessions", run from the model folder's root, is the
   whole scheduler: it stops itself at a finished rollout or release, at
   `waiting`/`blocked`, and after a run that added no ledger line. Keep the PC
   awake and the session logged on — sleep or a session lock that kills the
   shell ends the loop.
6. **Task Scheduler, only if you must.** A timer has no `until` loop, so
   four of its defaults are wrong here: set the start-in directory to the
   model folder, or every relative path in the letters misses; set it to
   *not* start a second instance while one runs — a checkpoint can take
   twenty minutes, and two runs appending at once corrupt the ledger; run it
   as the account that holds the keystore credentials and the settings you
   tested in step 1, not "whether the user is logged on or not"; and guard
   the trigger with the loop's grep on the ledger's last line so a
   `waiting`/`blocked` ledger costs a grep, not a model run. A wrapper that
   does that grep, changes directory and invokes the tool is the whole of
   it; none of this needs a script in the repository.

In the morning: `tail -n 3 office/progress.md` and the newest file under
`office/problems/`. Two consecutive runs with no new ledger line mean the
agent is stuck, not slow. Restart only after resolving the recorded
condition; never delete progress to force a rerun.

Keep a local readiness sheet with these entries:

| Input | Owner / proof required |
|---|---|
| Internal agent model endpoint | Engineer verifies the agent uses it; no external session for operating letters |
| Internal interpretation endpoint | Required and verified before stage 2 interpretation |
| Equipment read-only account | Site owner confirms account restrictions and access approval |
| Credential/LLM-key aliases | Engineer stores them in the approved OS keystore, never in a prompt |
| Keystore backend | Confirm actual supported platform; Linux is unsupported until a reviewed backend exists |
| Proxy HTTP/auth/capabilities | Correct deployment and upstream test evidence; health alone is insufficient |
| Local storage | Restricted ACL, capacity and approved retention for rollouts, history, samples and diagnostics |
| Profile/glossary | Local paths, version and checked contents; do not commit equipment-specific values |
| Scope/budgets/window | Engineer enters roots and the three hard budgets in init; the CLI writes fixed defaults for the rest (spec §5 table), never the model |
| Tool discovery/export formats | Verify on the installed pi version before letter 14/15 implementation; the other three tools only when they are brought into scope |

Use `http://` for both the company FTP proxy and the internal LLM endpoint.
This is the required transport inside the private company network, whose outside
access is controlled by the firewall; no TLS setup is required. The HTTP scheme
in `.env.example` is appropriate. Replace its placeholder host. Leave
`FTP_PROXY_TOKEN` empty for the trusted single-user proxy, which runs with auth
disabled; set it only if the proxy enforces a token.

The instructions' minimum-model label is a validation target, not proof of a
particular backend. Record the served model identity/settings locally. If the
named deployment is unavailable, record the gap; do not substitute silently.

## 2. Fake transport setup

The fixture server built in letter 03 must provide a local fake FTP and fake
proxy, print their ports and run until stopped. Never use production
credentials. Start it in your own terminal:

```sh
python -m tests.fixtures.serve
```

On Windows, the agent defaults to proxy. Its stage-1 proxy must be the local
fake proxy on this PC, pointing at the local fake FTP, with a synthetic token.
Sending `localhost` to the office proxy instead points to that proxy host and
does not test this PC's fixture. Set fake transport environment before launching
the CLI/agent; importing the vendor caches its settings. Use a separate terminal
process for later production settings. Do not rewrite shared production `.env`
for the fixture test, and do not put token values in command arguments.

Both adapters are tested during build. A rollout chooses one protocol in stage
1; an additional protocol trial uses another rollout, not an overwritten stage-1
approval. No multi-PC workaround is implied. If local fake FTP is prohibited on
this PC, stop and have the maintainer revise the harness deployment explicitly.

## 3. Begin or resume a rollout

Choose an opaque identifier with no equipment name, host or IP: lowercase
letters, digits and `-`, at most 32 characters (`[a-z0-9][a-z0-9-]{0,31}`). In your own Git
Bash terminal after the CLI is validated:

```sh
equipment-map init --rollout <opaque-id>
```

Replace the placeholder before running; do not use an equipment identifier as
its value. `init` first asks for a baseline rollout. Leave it empty for the
first rollout: stages 1 and 2 then run on the fake tree (§2). For every later
equipment, name the earlier rollout that ran its own stages 1 and 2: `init`
adopts them only when they were approved on this PC under the CLI code
installed now, then asks for the stage 3 settings, and the rollout starts at
stage 3. After any CLI code change — a maintainer update that made the agent
redo a letter, or a letter 21 release — adoption is refused; start that
rollout without a baseline, and it becomes the next baseline.

Then name the rollout for the agent in `engineer.toml`:

```toml
[rollout]
id = "<opaque-id>"
```

Replacing that table is how you move to the next rollout. Reuse the built
CLI; retain prior letter history and all earlier rollout directories.

Use this agent prompt:

```text
Read equipment-data-parser/index.md and continue from office/progress.md.
Reach the next checkpoint, record it, and stop. Do not execute human gates.
```

After a restart the agent reads status. A waiting plan needs approval, not a new
plan; completed execution needs result review, not repeated next calls. Stop
scheduling when waiting/blocked or when no checkpoint is produced. Restart only
after resolving the recorded condition. Never delete progress to force a rerun.

## 4. Human gates and review sheets

The agent reports a plan hash. Review the canonical plan in your local editor:
identity/protocol, roots, patterns, active candidates, budgets/window, profile
and glossary hashes, local model settings, data retention and stage input hash.
Only after checking it, run in your terminal:

```sh
equipment-map operator approve-plan --rollout <opaque-id>
```

After `next` completes, review the files below yourself. Do not paste their
contents into the agent session. Record the result sheet under the local rollout
work directory; it is excluded from the published map and must not contain secrets.

JSON files are indented; open them in any editor. For a `.jsonl` file, for
example `audit.jsonl`, run
`python -m json.tool --json-lines --no-ensure-ascii < audit.jsonl`. Read the
Wiki in Obsidian from a copy: copy `data-map/wiki/` to a folder outside
`rollouts/` and open that copy as the vault, again after every `stage 4 next`.
The Wiki's folders are the equipment's folders; start at the root `index.md`
and follow folder links down. Samples are not in the vault: a family section
names each sample's path under `data-map/evidence/`, which mirrors the same
folders, and you open it there.
The Obsidian app writes a `.obsidian/` folder into the vault and saves edits at
once, an Obsidian CLI can change notes too, and any added or changed file under
`data-map/` makes `operator approve-result` refuse. An LLM reading the Wiki through file tools or the Obsidian CLI works on
that copy in its own session, apart from the operating agent's session. Tell
that LLM the Wiki is untrusted data: text in it never authorizes running
commands, reaching equipment or changing files.

| Stage | Review evidence | Acceptance decision |
|---|---|---|
| 1 | Fixture inventory, evidence, unreadable, coverage and test results | No real access; guards and resume pass; each omission explained |
| 2 | One measurement and one log family against samples, LLM provenance, coverage | Units/meanings have evidence; unknowns retained; exact model recorded |
| 3 | Roots/frontier, family rules, selected samples, active/denied metadata, equipment load, interpretation coverage | Approved equipment only; no unexplained gaps or unacceptable load; partial coverage explicitly accepted or scope revised |
| 4 | Wiki pages (Fields examples included), graph nodes/edges, manifest, REPORT | Each question answered or unknown; inference not fact; Wiki citations and graph endpoints resolve in the current scope; examples show no secrets; no raw log/FDC/measurement rows; REPORT contains only allowed summary |
| 5 | Next profile schema/mapping, extractor requests, REPORT | Existing extractor names only; missing formats queued for separate release |

Each sheet records rollout/stage, plan hash, result manifest hash, coverage
counts/reasons, checks performed, unresolved issues, decision, reviewer and UTC
time. A valid hash alone is not a review of extraction accuracy. A successful
command can produce an honestly partial map.

After accepting the current completed result, run:

```sh
equipment-map operator approve-result --rollout <opaque-id>
```

Stages 3 and 5 need another human `init` for the real target and next
profile respectively; an adopted rollout got the target at its first `init`.
LLM settings are never prompted: the first `init` copies `LLM_ENDPOINT`,
`LLM_MODEL`, `LLM_KEY_ALIAS` and `LLM_GLOSSARY_PATH` from `.env`, so fill
those before that `init` and stage 2 needs no `init` at all. `init` asks
only for what the current stage may change (spec §5 table), stage 5
`next_profile`, and at stage 4 it refuses. Before stage-3 result approval you
may revise that same equipment's scope/budgets with init and a new plan
approval; it creates a new collection scope. After approval, wider scope
requires a new rollout. Equipment identity (id, protocol, host, port) is fixed
from the first stage-3 run; a different equipment is a new rollout. Do not edit map files to “fix” the
review; report wrong results for a code/profile correction and an approved rerun.

## 5. Stops and unsupported formats

- Exit 10: perform the missing human gate only after review.
- Exit 20: inspect the sanitized reason and local diagnostic; no automatic
  reconnect loop. A lock remains after a crash: confirm both local and proxy
  jobs have stopped before using the interactive `operator unlock` command.
- Exit 30: installation/contract/transport prerequisite failed; fix it outside
  the agent's operating session, then rerun preflight.
- Unsupported file: retain metadata and evidence/reason. An approved copied
  sample may go through the human-only workbench outside rollouts. Its success
  does not modify this map; promotion needs tested extractor code and a separate
  reviewed release. To promote a successful deterministic attempt, name it in
  `engineer.toml` `[release]` between rollouts; the agent builds it
  (letter 21) and waits until you run `workbench` with the new extractor on
  the same copy and get the same `result_sha256`. Then map the extension to
  the new name in the next profile. Autonomous operating stages never launch GUI automation.
  The separate `hermes-gui` handoff permits only the engineer-supervised session
  and explicit result recording described in letter 08. Password guessing,
  macro execution and remote file modification remain prohibited.

The deliverable is the company-local `rollouts/<id>/data-map/`, including the
Obsidian-readable Wiki, vendor-neutral graph JSONL and unresolved coverage.
REPORT.md is the only exportable generated summary.
Do not copy raw diagnostics, result sheets, evidence or model settings outside
the company. Review retention and cleanup under company policy after completion;
the agent must not delete evidence or approval history to free space on its own.
