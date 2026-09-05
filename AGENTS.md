# Equipment Data Map agent contract

## Purpose

Build a company-internal exploration kit that lets an LLM inspect one FAB
equipment file store thoroughly and safely. The deliverable is not just a
collector: provide the guide, portable skills, safe scripts, checkpoints,
review sheets, and evaluation cases needed for an engineer to supervise a
long-running exploration.

The minimum model target is the current Qwen3.8 28B class. Treat that as a
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
