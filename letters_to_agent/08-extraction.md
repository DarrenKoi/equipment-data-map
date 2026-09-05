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

## Done when

```
python -m pytest -q tests/test_extraction.py
```

Covers every fixture kind: text, CSV, JSON, XML with an external entity
(must not resolve), PNG, random bytes → `unreadable: encrypted`, truncated
zip → `unreadable: corrupt`, nested zip reads one level only, an archive
whose inner file exceeds the cap is cut at the cap. Same input twice gives
byte-identical output.
