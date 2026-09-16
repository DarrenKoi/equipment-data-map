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
enabled, is also the approved internal interpretation model before any other model is tried. Do not run the letters with several
models at once, and do not switch models mid-sequence: a half-built CLI or a
half-interpreted map from two models cannot be reviewed as one result.
Comparing models is a later exercise, on a finished process.

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
`equipment.toml`, `out/`, `.venv/` or the root build outputs, so every
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
| Scope/budgets/window | Engineer enters them in init; no defaults inferred by the model |
| Tool discovery/export formats | Verify on all four tool versions before letter 14/15 implementation |

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

Choose an opaque identifier with no equipment name, host or IP. In your own Git
Bash terminal after the CLI is validated:

```sh
export ROLLOUT=<opaque-id>
equipment-map init --rollout "$ROLLOUT"
```

Replace the placeholder before running; do not use an equipment identifier as
its value. Start the office agent from that environment. For a subsequent
rollout, append its human marker to progress as index.md specifies. Reuse the
built CLI; retain prior letter history and all earlier rollout directories.

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
equipment-map operator approve-plan --rollout "$ROLLOUT"
```

After `next` completes, review the files below yourself. Do not paste their
contents into the agent session. Record the result sheet under the local rollout
work directory; it is excluded from the published map and must not contain secrets.

| Stage | Review evidence | Acceptance decision |
|---|---|---|
| 1 | Fixture inventory, evidence, unreadable, coverage and test results | No real access; guards and resume pass; each omission explained |
| 2 | One measurement and one log family against samples, LLM provenance, coverage | Units/meanings have evidence; unknowns retained; exact model recorded |
| 3 | Roots/frontier, family rules, selected samples, active/denied metadata, equipment load, interpretation coverage | Approved equipment only; no unexplained gaps or unacceptable load; partial coverage explicitly accepted or scope revised |
| 4 | Wiki pages, graph nodes/edges, RAG claim records, manifest, REPORT | Each question answered or unknown; inference not fact; graph endpoints and typed citations resolve in the current scope; no raw log/FDC/measurement rows; REPORT contains only allowed summary |
| 5 | Next profile schema/mapping, extractor requests, REPORT | Existing extractor names only; missing formats queued for separate release |

Each sheet records rollout/stage, plan hash, result manifest hash, coverage
counts/reasons, checks performed, unresolved issues, decision, reviewer and UTC
time. A valid hash alone is not a review of extraction accuracy. A successful
command can produce an honestly partial map.

After accepting the current completed result, run:

```sh
equipment-map operator approve-result --rollout "$ROLLOUT"
```

Stages 2, 3 and 5 need another human `init` for LLM settings, the real target,
and next profile respectively. Before stage-3 result approval you may revise
that same equipment's scope/budgets with init and a new plan approval; it creates
a new collection scope. After approval, wider scope requires a new rollout.
Never change equipment identity mid-pilot. Do not edit map files to “fix” the
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
  reviewed release. Autonomous operating stages never launch GUI automation.
  The separate `hermes-gui` handoff permits only the engineer-supervised session
  and explicit result recording described in letter 08. Password guessing,
  macro execution and remote file modification remain prohibited.

The deliverable is the company-local `rollouts/<id>/data-map/`, including Wiki,
vendor-neutral graph JSONL, claim-oriented RAG JSONL and unresolved coverage.
REPORT.md is the only exportable generated summary.
Do not copy raw diagnostics, result sheets, evidence or model settings outside
the company. Review retention and cleanup under company policy after completion;
the agent must not delete evidence or approval history to free space on its own.
