# Equipment Data Map agent contract

This root contract guides agents maintaining the repository. The office agent
executing the build-and-operate letters starts with
`equipment-data-parser/AGENTS.md` and `equipment-data-parser/index.md`.

`equipment-data-parser/AGENTS.md` is the execution contract for the company-local
LLM agent: building the mapper in letters 01–15, then operating it in letters
16–20 within engineer-approved scope and budgets. It defines how that agent
resumes work, proves completion, and respects human gates. Keep it usable with
the letters without requiring the office agent to read this root contract.
When maintaining the letters, keep their execution contract consistent with
the workflow; do not start executing the letters unless the user asks.

## Purpose

Build a company-internal exploration kit that lets an LLM inspect one FAB
equipment file store thoroughly and safely. The deliverable is not just a
collector: provide the guide, portable skills, safe scripts, checkpoints,
review sheets, and evaluation cases needed for an engineer to supervise a
long-running exploration.

The initial minimum-model validation profile is the dedicated company
Qwen3.8-27B deployment; record its exact served model identifier. Treat that as a
capability floor, not a fixed model dependency. Validate newer Qwen, GLM, Kimi,
GPT, and other approved models against the same observable scenarios and record
the exact model and serving configuration used by each run.

## Read first

Read `docs/architecture/equipment-data-map.md` before changing architecture,
skills, collection behavior, extraction behavior, checkpoints, approval gates,
or evaluation criteria. It is the source of truth for the runtime pipeline and
the five rollout stages.

## Operating model

- One engineer owns one rollout on one PC from stage 1 through stage 5.
- The engineer supplies the approved equipment root paths and any likely
  real-time data paths. Exploration stays inside those roots and budgets.
- Equipment access is read-only. Collection begins with metadata and downloads
  only approved representative samples.
- A newest or actively changing file is an `active_candidate`: collect metadata
  only while it may still be written. Infer periodic updates from timestamp
  series or repeated inventories, and record `unknown` when evidence is weak.
- Keep credentials, source data, extracted content, prompts, and analysis inside
  the company network and approved local storage.

## Control plane and exploration

Keep the control plane deterministic: code enforces allowed roots, budgets,
locks, approvals, audit records, checkpoints, and resume behavior. LLMs may
choose investigation and interpretation methods only inside those enforced
limits.

Make long work resumable at directory, file-family, and extraction-attempt
boundaries. Every attempt records its input reference, method, result, failure
reason, and next safe action so a later session can continue without relying on
chat history.

Use deterministic extractors first. For unsupported formats, copy an approved
representative sample locally and use the extractor workbench to try additional
methods, including Hermes computer use with approved GUI tools. Experimental
extractors operate on the local copy. Promote a successful extractor only
through a separate reviewed and tested CLI release; otherwise leave an
`unsupported-format` report with evidence.

## Letters to agent

`equipment-data-parser/` is the ordered build-and-operate sequence for the
company-internal LLM. It is self-contained: `index.md` is the entry point,
`spec.md` is a snapshot of the architecture doc, and `progress.md` is the
append-only state ledger. Rules that every tool honours when working there:

- Start from `index.md`; take the first letter without a `done` line.
- Disk plus `progress.md` is the only state. Write a `wip` line and commit
  at each checkpoint — inside a build item as well as at its end — so any
  session can end at any moment and the next one resumes from the `next:`
  field. Context windows are disposable.
- A session may be one non-interactive prompt (`claude -p`, `codex exec`,
  `opencode run`) re-run until the work is finished. It reaches the next
  checkpoint, commits, and stops; it never asks, waits, or polls.
- A letter is `done` only when its **Done when** commands pass verbatim.
- Operating letters (16 onward) run only the skill-allowed subcommands and
  never `init` or `operator` commands.
- Keep `spec.md` in sync with `docs/architecture/equipment-data-map.md`;
  the `docs/` copy wins.
- The office agent reports what the letters got wrong about its site in
  `equipment-data-parser/problems/NN-problems.md`, one file per letter. Those
  entries are the input for fixing a letter or the spec; the office agent does
  not edit the letters itself.

## Skill deliverables

- Publish portable Agent Skills usable from Codex, Claude Code, OpenCode, and
  pi through the company Skill Market.
- Keep each stage skill narrow: goal, prerequisites, permitted commands,
  checkpoint, review sheet, stop conditions, and completion evidence.
- Keep state and safety decisions in scripts rather than model prose. Skills
  guide the model; scripts make unsafe or invalid transitions fail closed.
- Keep tool-specific installation metadata outside the shared skill body unless
  the target platform requires it.

## Completion evidence

A change is complete only when its smallest relevant scenario proves the
behavior. Prefer fake FTP/SMB trees and copied samples before any approved
equipment trial. Verify read-only access, budget stops, checkpoint resume,
unreadable-file retention, evidence traceability, and rejection of invalid stage
transitions. Skill releases also need the same task scenario exercised across
the four supported agent tools and the current minimum-model profile.
