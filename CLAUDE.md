# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

`AGENTS.md` is the contract shared with Codex, OpenCode, and pi. Put cross-tool rules there — including which language a file is written in. This file adds only Claude Code orientation.

## Repo status

Docs, one vendored library (`ftp_handler/`) and `spike.py`; no CLI and no build or lint command. The transport check runs with `python tests/test_ftp_transport.py`. `spike.py` (letter 00) runs as `python spike.py equipment.toml`; its home check is `uv run --python 3.11 --with pyftpdlib --with flask --with requests python tests/test_spike_fake.py` (fake FTP, real proxy blueprint, fake LLM). `equipment-data-parser/` fixes the stack the office build uses (Python 3.11, pytest), but the `equipment-map` CLI from letter 01 onward is built in the office PC's model folder and never comes back by git, so this repo gets no pytest suite from it. The home checks are the bare scripts listed in `README.md`. The architecture doc is the spec the letters must lead that build to satisfy.

## Where things are

`ftp_handler/` is the FTP library copied from `skewnono_v3_nuxt` — the intended FTP
Source adapter for §4, currently used by `spike.py`. `size_dirs` returns a UTC
`modified` per file, so the metadata pass gets path, size and mtime in one
connection on either transport (`tests/test_sizing_mtime.py`); that change is
already ported to `flask_modules` and `skewnono_v3_nuxt`. `core` (`FtpClient`, one server) and
`direct_downloader` (`FtpFleetDownloader`, concurrent fan-out) are stdlib-only; `proxy`
carries the same `FtpFleetDownloader` surface over HTTP and needs `requests` on the
client, `flask` on the server. The upstream `web_app` subpackage was left behind.

**Transport is a platform fact, not a call-site choice.** The Windows engineer PCs have
no FTP egress and must go through the proxy; Linux hosts reach the equipment directly.
Call `ftp_handler.fleet_downloader()` for the right class instead of importing one of
the two by hand; `FTP_TRANSPORT=proxy` forces the proxy on a non-Windows machine
behind the firewall, and `direct` is refused on Windows since the company allows no direct FTP from engineer PCs. Deployment facts stay out of the source
tree: copy `.env.example` to `.env` (untracked) for `FTP_PROXY_URL` and
`FTP_PROXY_TOKEN` — `ftp_handler.load_dotenv()` folds it into the environment at
import, and a real env var wins. `tests/test_ftp_transport.py` pins that branch
and runs bare (`python tests/test_ftp_transport.py`).

`equipment-data-parser/` is the self-contained build-and-operate sequence for the company LLM: `index.md` is both the office agent's contract and the workflow, then letters in order, tracking state in `office/progress.md`. `equipment-data-parser/spec.md` is a snapshot of the architecture doc; refresh it when the doc changes. `office/` (ledger, problem entries, `spike.py` workaround) exists only in the office PC's model folders — never create it here; read the summaries the user relays before rewriting a letter.

`docs/architecture/equipment-data-map.md` (Korean) is the source of truth. `docs/architecture/equipment-data-parser-llm-behavior.md` (Korean) is a one-page guide to how the letters drive the agent LLM, what the internal LLM receives, and which Markdown comes out (no HTML is generated). Section map of the spec:

| Need | Section |
|---|---|
| Runtime pipeline (6 steps) and module seams (Source, Inventory, Grouping, Sampling, Extraction, LLM, Data Map) | §3, §4 |
| CLI subcommands, exit codes, stdout rules | §5 |
| Rollout directory layout and state truth | §5.1 |
| Safeguards (allowlist, lock, approval hash) | §6 |
| Verification scenarios against a fake FTP tree | §7 |
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
