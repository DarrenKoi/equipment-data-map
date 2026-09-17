# Letter 08: Deterministic extraction

## Goal

Extract structure from every sample with deterministic tools under the
safety limits, and classify what cannot be read.

## Read

`spec.md` §4.5 in full, §2 principle 7, §10 (type distinctions).

## Build

Use implementation-reference.md §6 for exact limits, output, reason codes,
decoding order, key/value patterns and field value rules.

- `equipment_map/extract/` with one module per kind: text/log (BOM, UTF-8
  then CP949 decoding, bounded read, key/value lines and inline `name=value`
  pairs), CSV/TSV (every column name, inferred types, few rows), JSON/XML/INI
  (key structure, sample values; XML entity declarations refused), archive
  (listing only; inner samples within the output byte cap; nesting depth 1),
  image (dimensions, format), unknown binary (magic bytes, printable strings,
  entropy).
- Dispatcher by signature first, extension second.
- Line-based input larger than the parser input cap is parsed up to the cap
  and reported `partial`, so headers and field names survive; JSON and XML
  over the cap stay `too-large`.
- `unreadable` result with reason in `encrypted`, `corrupt`, `unsupported`,
  `too-large`. High entropy alone → `unsupported`, with an optional low-
  confidence encryption hypothesis. `encrypted` requires a recognized format's
  encryption flag; random bytes are not proof.
- Nothing is ever executed; archives are listed with `zipfile`, never
  extracted to disk.
- Extraction results are written next to the evidence file as
  `<sha>.extract.json` with `method`, `result`, `failure_reason`, and
  `next_safe_action`.
- For supported formats, emit the bounded observed descriptors in spec
  §4.5/§4.7.2: exact field path/name, observed type, explicit unit and
  schema/version strings; distinct source time fields and observed span;
  equipment/module/chamber/channel/sensor/recipe/lot/wafer/run/site identifier
  fields; explicit status, alarm, quality, limit and pass/fail fields; record,
  null and invalid counts; references; and component/parameter structure.
  Every field gets up to three example values and per-type counts over all
  parsed values; a field with any numeric value also gets max decimals,
  min/max and its numeric value count, whatever its category, and no other
  statistics.
  Never infer meanings or copy all log events/time-series rows.
- A configuration diff is allowed only between approved samples in the same
  family with compatible observed schemas. Bound added/removed/changed keys by
  the normal result limits and cite both sample and extract hashes. Do not
  infer whether a changed value is a setpoint or readback unless the source
  states that role.
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
(must not resolve), PNG, random bytes → `unreadable: unsupported`, a known
encrypted archive → `unreadable: encrypted`, truncated
zip → `unreadable: corrupt`, nested zip reads one level only, an archive
whose inner file exceeds the cap stops without publishing a complete inner sample.
CP949 text yields fields with `encoding: cp949`; a UTF-16 file with a BOM is
decoded as text, not binary; a two-line `GAIN = 12.4` / `OFFSET = 0.5` file
yields both fields; `set-point=12.4` in a log line yields `set-point` while
`set/point=12.4` and `key="abc"oops` yield nothing; `1e309` counts as invalid
and stays out of min/max while `offline` and `1,234` count as `string`; a CSV
over the input cap is `partial` and keeps its header; a 300-column CSV keeps
all 300 names; `<!DOCTYPE root>` XML parses while an entity declaration is
refused; a column mixing empty, `N/A`, `*****`, `offline`, `12.40` and `1.5e3`
cells reports type counts, max decimals 2, min/max and null/invalid counts
over every parsed row; `1.230e-2` gives max decimals 3; extract JSON with
numbers serializes without error. Same input twice gives
byte-identical output; `workbench` refuses a copy dir under `rollouts/`,
appends without rewriting earlier records, and `hermes-gui` produces
`handoff.json` and no extraction output.

Add category-shaped fixtures for log/alarm, FDC, measurement, configuration,
recipe, software/firmware, maintenance/calibration and reference data. The
extractor reports observed structure for each without assigning semantic
category, lifecycle or causal meaning.
