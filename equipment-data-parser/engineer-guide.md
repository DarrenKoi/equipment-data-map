# Engineer handoff

This file is for the supervising engineer. The office agent starts at
[index.md](index.md). These are instructions for a CLI to be built, not a claim
that it is installed or ready. Do not run the operating commands below until
letters 01–15 and their gates pass. Keep filled site information local and
untracked; this repository contains blank guidance and synthetic examples only.

## 1. Before the first office session

Prepare one company PC, a company-approved local model connection for the agent,
Python 3.11+, Git Bash on Windows, pip access to approved packages, and Git user
identity. Check the repository root is the task's working directory. Use one
running agent instance. Verify permissions with one supervised build checkpoint
before scheduling it; do not grant blanket approval to equipment operations.

The initial repository contains the vendor FTP package and five transport tests.
There is no `equipment-map` CLI, extraction suite or released skill suite yet.
The separate metadata and execution-lifecycle gaps in implementation-reference.md
§4 need upstream/deployment verification. File-size capping is not a prerequisite:
use normal downloads, including eligible large/unknown-size files, with actual-byte
accounting and best-effort targets. No cap workaround is required. Mock tests
can guide implementation but cannot waive that blocker.

### Git on the office PC

The office PC pulls from the maintainer's remote and never pushes. The agent
writes in `office/` (ledger, problem entries, a changed `office/spike.py`)
plus the new files the build letters create, and commits on a local office
branch. Findings travel home by hand: relay a sanitized summary of
`office/problems/` and the `office/progress.md` result to the maintainer, with
no equipment addresses, paths or credentials.

**One model, one worktree.** Every agent model that runs the letters gets its
own git worktree on its own branch `office-<model>`, so parallel runs never
share a ledger, a `office/spike.py`, root build outputs, `out/` or
`rollouts/`. The working directory is the whole identity: the prompt never
names the model, and an agent launched in `<repo>-<model>/` is that model's
run. The first line of that worktree's `office/progress.md` names the model,
and `equipment.toml` in that worktree names the served model for `spike.py`.
`<model>` is a short slug of letters, digits and dashes (`qwen3-8b`), never
a host, path or credential.

Set each up once, in Git Bash at the clone's root, with a clean tree. If this
clone already holds agent work on a plain `office` branch, leave it: the
checks accept `office` as well as `office-<model>`, and it keeps working as
one more worktree.

```sh
M=qwen3-8b                                            # the model slug for this worktree
(
  set -e
  test -z "$(git status --porcelain)"
  git config --local remote.origin.pushurl DISABLED   # git push to origin fails
  git config --local push.default nothing             # a bare git push fails
  git fetch origin
  git worktree add --no-track -b "office-$M" "../$(basename "$PWD")-$M" origin/main
  cp .env "../$(basename "$PWD")-$M/" 2>/dev/null || true   # untracked site files travel by copy
  cd "../$(basename "$PWD")-$M"
  mkdir -p office/problems
  printf '# Progress\n\nModel: %s. Append-only. Format is in equipment-data-parser/index.md.\n' "$M" > office/progress.md
  git add -- office/progress.md
  git commit -q -m "office: start the ledger for $M"
)
```

Then copy `equipment.toml` into the new worktree and set its `llm` section to
that model. Launch that model's agent tool, one-shot loop or scheduled task
with the new worktree as the working directory; the letters say "repository
root" and mean that directory.

The push guard stops accidents only. Give this PC read-only access to the
remote so a deliberate push also fails.

Merge maintainer updates between agent sessions: disable every schedule first
and let any running agent and its child processes finish. This walks every
office worktree; a failed merge names its directory and the loop goes on.

```sh
git fetch origin
git worktree list --porcelain | sed -n 's/^worktree //p' | while read -r w; do (
  set -e
  cd "$w"
  case "$(git branch --show-current)" in office|office-*) ;; *) exit 0 ;; esac
  test -z "$(git status --porcelain)"
  git -c merge.autoStash=false merge --no-edit origin/main
) || echo "merge failed in $w"; done
```

The maintainer never writes in `office/`, so the merge is normally clean. On
any conflict, run `git merge --abort` in that worktree and reconcile by hand
before the next session; choosing a side wholesale can discard work. When the merge changed
`spike.py` and `office/spike.py` exists, compare them
(`git diff --no-index spike.py office/spike.py`): delete the copy if the
maintainer's version covers the workaround, otherwise port the new changes
into it. Run the home checks against the merged tree before restarting the
schedule.

Keep a local readiness sheet with these entries:

| Input | Owner / proof required |
|---|---|
| Internal agent model endpoint | Engineer verifies the agent uses it; no external session for operating letters |
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
| 4 | Wiki index/family pages, RAG evidence links, manifest, REPORT | Each question answered or unknown; inference not fact; hashes resolve; REPORT contains only allowed summary |
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
RAG and unresolved coverage. REPORT.md is the only exportable generated summary.
Do not copy raw diagnostics, result sheets, evidence or model settings outside
the company. Review retention and cleanup under company policy after completion;
the agent must not delete evidence or approval history to free space on its own.
