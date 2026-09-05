# Letter 15: Cross-tool scenario validation

## Goal

Prove the skills behave under the minimum model across the four agent
tools. You prepare the harness; a human runs the sessions and records the
model configuration.

## Read

`spec.md` §7 (agent-tool checks, observable results), §10.

The minimum model is the company Qwen3.8 28B class; treat it as a floor.
Newer Qwen, GLM, Kimi, GPT, or other approved models are validated against
the same scenarios, recording the exact model and serving configuration.

## Build

- `scenarios/README.md`: one scenario per §7 observable result, each with
  the exact prompt to give the agent tool, the rollout fixture to prepare,
  and the expected `audit.jsonl` events.
- `scripts/check_audit.py`: reads an `audit.jsonl` and the tool's shell
  transcript, fails if any command is outside the skill's allowed set,
  if `next` succeeded without a prior `approve-plan`, or if an LLM field has
  more than two attempts.
- `scenarios/results/<tool>-<model>.md` template with fields: tool and
  version, model id, serving config, scenario pass/fail, transcript path.

## Done when

```
python -m pytest -q tests/test_check_audit.py
```

Then hand off to the human. This letter is `done` only after a human
appends to `progress.md` one line per tool (Codex, Claude Code, OpenCode,
pi) with the model id and serving config used and all scenarios passing. If
that is not yet possible, record `waiting` with what the human must run and stop.
