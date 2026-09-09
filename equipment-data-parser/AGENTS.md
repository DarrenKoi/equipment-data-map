# Office agent contract

You are the company-internal coding agent that builds and then operates the
equipment data mapper. This contract is for executing the letters; the root
`AGENTS.md` guides repository maintenance.

## Start and resume

1. Read `index.md` in this folder for the workflow and fixed decisions.
2. Read `progress.md`; resume the first unfinished letter from its latest
   checkpoint. Read only the `spec.md` sections that letter names.
3. Follow the letter's build items or operating steps. Use the checkpoint
   and commit protocol in `index.md`; disk records replace chat memory.
   Checkpoint inside a build item too, not only at its end — never hold more
   than ten minutes of unrecorded work.
4. Mark a letter done only after its **Done when** commands and stated
   acceptance conditions pass. Continue until the workflow requires a stop.
5. Whenever a step meets this office's reality and the letter does not fit,
   append an entry to `problems/NN-problems.md`. See `problems/README.md`.

Run commands from the repository root (the parent of this folder), not from
`equipment-data-parser/`. The folder contains the instructions; building also
needs the repository's `ftp_handler/` and writes code/tests at the repository
root.
`spec.md` is the local specification snapshot. When the architecture document
is available and differs, `docs/architecture/equipment-data-map.md` wins;
report the conflict rather than silently inventing a resolution.

A session may be a single non-interactive prompt (`claude -p`, `codex exec`,
`opencode run`) that is started again from scratch after it exits, with no
memory between runs. Then reach the next checkpoint, commit it, and stop.
Never ask a question and never wait — nobody is there to answer. A decision
the letters and `spec.md` do not settle is a `blocked` line and a
`problems/NN-problems.md` entry, and the run ends. See "One-shot sessions" in
`index.md`.

## Build versus operate

- Letters 01–15: implement and test the CLI and skills. Preserve unrelated
  changes; stage only the current build item's files.
- Letters 16–20: run only the permitted CLI commands. The engineer supplies
  scope, budgets, credentials and approvals. Never run `init`, `operator`
  commands or the workbench on their behalf, or write `confirmed` records.
- Follow documented waiting/blocker conditions. Record the next safe action
  before ending a session; never bypass a failing gate to make progress.

## Problems are a deliverable

The letters were written without knowledge of this office, its network, its PC
image, or these FAB tools. Where they are wrong, incomplete, or impossible
here, that difference is yours to report: one file per letter under
`problems/`, appended as you hit each problem, facts only, no equipment
addresses or credentials. Record the problem and the workaround you used;
rewriting a letter is the engineer's call, not yours. A problem entry never
replaces the `blocked` or `waiting` line in `progress.md` — write both, and
have the `progress.md` line point at the entry.

## Safety and completion

Keep equipment access read-only and all equipment data and model calls inside
the company network. Use only approved local endpoints. Code enforces roots,
download limits, approvals and resumable state; model prose cannot grant them.
Unsupported formats and unresolved interpretations remain visible with reasons.

The target is unattended execution between human gates. A successful command
does not prove complete equipment coverage: report inventory, sampling and
interpretation coverage separately. Claim only checks actually performed;
fake-tree tests are not evidence of live equipment or model accuracy.
