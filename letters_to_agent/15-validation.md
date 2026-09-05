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
- Normalized transcript: `scenarios/transcripts/<tool>-<model>-<scenario>.jsonl`,
  one object per line, keys exactly `seq`, `ts` (UTC ISO-8601), `role`
  (`user`|`assistant`|`command`), `text`, `command` (shell line, `command`
  role only), `exit_code`. `scripts/normalize_transcript.py --tool
  <codex|claude-code|opencode|pi> <native-export>` converts each tool's own
  session export (`scenarios/README.md` states, per tool, the export
  command or session file location the human uses) into that format; the
  script fails on an unknown tool instead of guessing.
- `scripts/check_audit.py`: reads an `audit.jsonl` and one normalized
  transcript, fails if any `command` line is outside the skill's allowed
  set, if `next` succeeded without a prior `approve-plan`, or if
  `llm-attempts.jsonl` shows a third attempt for any field.
- `scenarios/results/<tool>-<model>.md` template with fields: tool and
  version, model id, serving config, scenario pass/fail, normalized
  transcript path.

## Done when

```
python -m pytest -q tests/test_check_audit.py tests/test_normalize_transcript.py
```

Then hand off to the human. This letter is `done` only after a human has
appended these four `confirmed` lines to `progress.md`, each with real
values in place of the angle-bracket fields and `all-scenarios-pass`
literally:

```
- 15 confirmed <UTC date> | codex <tool version> | <model id> | <serving config> | all-scenarios-pass
- 15 confirmed <UTC date> | claude-code <tool version> | <model id> | <serving config> | all-scenarios-pass
- 15 confirmed <UTC date> | opencode <tool version> | <model id> | <serving config> | all-scenarios-pass
- 15 confirmed <UTC date> | pi <tool version> | <model id> | <serving config> | all-scenarios-pass
```

Until all four exist, record `waiting` whose check is
`grep -c '^- 15 confirmed .* | all-scenarios-pass$' letters_to_agent/progress.md`
equalling 4, and stop.
