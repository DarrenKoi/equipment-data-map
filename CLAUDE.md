# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

`AGENTS.md` is the contract shared with Codex, OpenCode, and pi. Put cross-tool rules there. This file adds only Claude Code orientation. Agent files (`AGENTS.md`, `CLAUDE.md`, `SKILL.md`) are English; design docs under `docs/` are Korean.

## Repo status

Docs plus one vendored library (`ftp_handler/`), no CLI yet. There is no build, lint, or test command. `letters_to_agent/` fixes the stack the code will use (Python 3.11, pytest); once letter 01 lands, `python -m pytest -q` is the test command. The architecture doc is the spec the code must satisfy. When the `equipment-map` CLI lands, record its build, test, and single-test commands here.

## Where things are

`ftp_handler/` is the FTP library copied from `skewnono_v3_nuxt` — the intended FTP
Source adapter for §4, not yet wired to anything. `core` (`FtpClient`, one server) and
`direct_downloader` (`FtpFleetDownloader`, concurrent fan-out) are stdlib-only; `proxy`
carries the same `FtpFleetDownloader` surface over HTTP and needs `requests` on the
client, `flask` on the server. The upstream `web_app` subpackage was left behind.

**Transport is a platform fact, not a call-site choice.** The Windows engineer PCs have
no FTP egress and must go through the proxy; Linux hosts reach the equipment directly.
Call `ftp_handler.fleet_downloader()` for the right class instead of importing one of
the two by hand; `FTP_TRANSPORT=direct|proxy` overrides the guess for a machine sitting
on the unexpected side of the firewall. `tests/test_ftp_transport.py` pins that branch
and runs bare (`python tests/test_ftp_transport.py`) until pytest lands.

`letters_to_agent/` is the self-contained build-and-operate sequence for the company LLM: it reads `index.md`, then letters in order, tracking state in `progress.md`. `letters_to_agent/spec.md` is a snapshot of the architecture doc; refresh it when the doc changes.

`docs/architecture/equipment-data-map.md` (Korean) is the source of truth. Section map:

| Need | Section |
|---|---|
| Runtime pipeline (6 steps) and module seams (Source, Inventory, Grouping, Sampling, Extraction, LLM, Data Map) | §3, §4 |
| CLI subcommands, exit codes, stdout rules | §5 |
| Rollout directory layout and state truth | §5.1 |
| Safeguards (allowlist, lock, approval hash) | §6 |
| Verification scenarios against fake FTP/SMB | §7 |
| Rollout stages 1–5 | §8 |
| Skill suite layout and per-skill allowed commands | §9 |
| Done criteria | §10 |

## Invariants that cut across every file

- **Two stage axes.** The 6-step runtime pipeline runs inside one CLI invocation. The 5 rollout stages are what the six skills map to. Keep them apart.
- **One CLI, thin skills.** All logic lives in `equipment-map`. Each `SKILL.md` runs only the subcommands its row in the spec's §9 table allows. A skill contains no branching, state machine, JSON assembly, or cross-skill call, and there is no `equipment-map-common` skill.
- **`audit.jsonl` is the rollout stage/approval state.** Append-only ledger under `rollouts/<id>/`; `status` derives the current stage from it. There is no mutable `state.json`.
- **Operator commands stay human.** `init`, `operator approve-plan`, `operator approve-result`, `operator unlock` appear in no skill and in no CLI `NEXT:` line. A skill invoking one is a scenario failure.
- **`rollout.json` is the only input to `plan`.** Roots, budgets, allow/deny patterns, and credential aliases come from that file, never from command flags.
- **Fixed exit contract.** `0` done or safe no-op, `10` await approval, `20` stop, `30` preflight failed. Last stdout line is `NEXT: <command | WAIT-APPROVAL | STOP | INSTALL-OR-UPGRADE>`.
- **stdout carries counts and hashes only.** Equipment paths, filenames and approved samples stay in local rollout files. Raw LLM prompts/responses are not retained by default; approved retention is outside rollouts. Validated fields are stored for mapping and recovery.
