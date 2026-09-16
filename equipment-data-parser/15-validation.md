# Letter 15: Cross-tool scenario validation

## Goal

Prove the skills behave under the minimum model on pi. You prepare the
harness; a human runs the sessions and records the model configuration.
Codex, Claude Code and OpenCode are out of scope for now: the harness keeps
room for them, and each is validated the same way when it is brought in.

## Read

`spec.md` §7 (agent-tool checks, observable results), §10, and
implementation-reference.md §9 before building the normalizers.

The initial minimum-model profile is the engineer's dedicated Qwen3.8-27B
deployment. Record its exact served model identifier; parameter-count
shorthand is not a verified identity or accuracy result.
Newer Qwen, GLM, Kimi, GPT, or other approved models are validated against
the same scenarios, recording the exact model and serving configuration.

## Build

Before coding the normalizer, obtain an engineer-provided synthetic native
export and exact tool/export version for pi. Record `waiting` if it is
missing; never infer an export schema from the tool name. Keep samples local
and untracked. The human confirms availability with
`- 15 confirmed <UTC date> | export-fixtures: ready | <local inventory sha256>`.
The fixture inventory records pi's version and sample hashes.

- `scenarios/README.md`: one scenario per §7 observable result, each with
  the exact prompt to give the agent tool, the rollout fixture to prepare,
  and the expected `audit.jsonl` events.
- Normalized transcript: `scenarios/transcripts/<tool>-<case-id>.jsonl` (local, untracked),
  one object per line, keys exactly `seq`, `ts` (UTC ISO-8601), `role`
  (`user`|`assistant`|`command`), `text`, `command` (shell line, `command`
  role only), `exit_code`. `scripts/normalize_transcript.py --tool pi
  <native-export>` converts pi's own session export (`scenarios/README.md`
  states the export command or session file location the human uses) into
  that format. `--tool` accepts `pi` and fails on every other name, including
  `codex`, `claude-code` and `opencode`: an out-of-scope tool is the same
  failure as an unknown one, and a guessed branch is worse than no branch.
  Bringing a tool in means a verified export sample first, then its branch.
- `scripts/check_audit.py`: reads an `audit.jsonl` and one normalized
  transcript, fails if any `command` line is outside the skill's allowed
  set, if `next` succeeded without a prior `approve-plan`, or if
  the LLM audit view exceeds two semantic slots or the approved per-slot
  transport limit, contains requests beyond cumulative budget, or repeats a
  committed result. Compare it with authoritative `work/llm.sqlite`, including
  recovery after an interrupted export.
- `scenarios/results/<tool>-<case-id>.md` local, untracked result sheet with fields: tool and
  version, model id, serving config, scenario pass/fail, normalized
  transcript path.

## Done when

```
python -m pytest -q tests/test_check_audit.py tests/test_normalize_transcript.py
```

Then hand off to the human. This letter is `done` only after a human has
appended this `confirmed` line to `office/progress.md`, with real values in
place of the angle-bracket fields and `all-scenarios-pass` literally:

```
- 15 confirmed <UTC date> | pi | <local result sheet sha256> | all-scenarios-pass
```

Record `waiting` until that current-release confirmation exists, tied to its
actual result sheet. When a further tool is brought into scope it adds its own
line in the same shape; a line copied from pi's does not pass for it.
The engineer verifies sheet hashes, suite/contract versions and the same exact
minimum-model profile in those sheets; model identity/configuration stays there,
not in tracked progress. Read implementation-reference.md §9 for the matrix.
