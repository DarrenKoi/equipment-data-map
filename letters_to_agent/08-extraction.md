# Letter 08: Deterministic extraction

## Goal

Extract structure from every sample with deterministic tools under the
safety limits, and classify what cannot be read.

## Read

`spec.md` §4.5 in full, §2 principle 7, §10 (type distinctions).

## Build

- `equipment_map/extract/` with one module per kind: text/log (encoding
  detection, bounded read), CSV/TSV (columns, inferred types, few rows),
  JSON/XML/INI (key structure, sample values; XML with external entities
  disabled), archive (listing only; inner samples within the output byte cap;
  nesting depth 1), image (dimensions, format), unknown binary (magic bytes,
  printable strings, entropy).
- Dispatcher by signature first, extension second.
- `unreadable` result with reason in `encrypted`, `corrupt`, `unsupported`,
  `too-large`. High-entropy unknown binary → `encrypted` guess with low
  confidence.
- Nothing is ever executed; archives are listed with `zipfile`, never
  extracted to disk.
- Extraction results are written next to the evidence file as
  `<sha>.extract.json` with `method`, `result`, `failure_reason`, and
  `next_safe_action`.
- `equipment_map/workbench.py` and engineer-only subcommand
  `equipment-map workbench <copy-dir> --method <name>`: works on an
  approved local copy of one sample (a directory the engineer created
  outside `rollouts/`; a path under `rollouts/` is refused). Appends one
  record per attempt to `<copy-dir>/attempts.jsonl`: `{ts, input_sha256,
  method, method_config, result_sha256|null, failure_reason|null,
  next_safe_action}`; never overwrites. Methods: every deterministic
  extractor with explicit options, and `hermes-gui`, which writes
  `<copy-dir>/handoff.json` (input sha, approved GUI tool name given by
  the engineer, allowed output path) and records the attempt as
  `handed-off`; the human-supervised Hermes session runs outside the CLI
  and the engineer records its outcome with `equipment-map workbench
  <copy-dir> --record <result-file>`. The workbench never writes under
  `rollouts/` or `data-map/`; a working method reaches production only as
  a new module in `equipment_map/extract/` with its test and a contract
  version bump in a separate reviewed CLI release. `workbench` is in no
  skill allowlist.

## Done when

```
python -m pytest -q tests/test_extraction.py
```

Covers every fixture kind: text, CSV, JSON, XML with an external entity
(must not resolve), PNG, random bytes → `unreadable: encrypted`, truncated
zip → `unreadable: corrupt`, nested zip reads one level only, an archive
whose inner file exceeds the cap is cut at the cap. Same input twice gives
byte-identical output; `workbench` refuses a copy dir under `rollouts/`,
appends without rewriting earlier records, and `hermes-gui` produces
`handoff.json` and no extraction output.
