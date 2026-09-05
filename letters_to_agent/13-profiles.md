# Letter 13: Equipment profiles, access window, stage 3 and 5

## Goal

What stage 3 and stage 5 need beyond stage 1: equipment profiles, the
access window in the plan hash, and connection diagnostics that stop
instead of retrying.

## Read

`spec.md` §8 stage 3 and stage 5, §4.4 (engineer inputs), §6, §11 (out of scope).

## Build

- `equipment_map/profiles.py`: profile registry file `profiles/<type>.json`
  with allowed path patterns, filename token rules, extractor mapping.
  `rollout.json` names a profile; grouping and extraction consult it.
- Access window: `always` or a UTC window, included in the canonical plan;
  `next` refuses to start outside the window (exit 20).
- `stage 3 next`: the stage 1 pipeline against the real `Source` from
  `rollout.json` (`host`, `port`, `share`), then `interpret_families` from
  letter 11 over families that have no interpretation yet, then
  `write_manifest`. Connection failure writes a diagnostic file, one audit
  entry, exit 20. No firewall or approval-system calls exist anywhere.
- `stage 5 plan`: refused unless `rollout.json.next_profile` names an
  existing `profiles/<type>.json` that differs from `profile`.
- `stage 5 next`: validate that profile's schema and that every extractor
  it maps is a name in `equipment_map/extract/`; write
  `data-map/extractor-requests.json` listing every family in
  `unreadable.json` with reason `unsupported` (key, count, evidence sha);
  `write_manifest`; write `REPORT.md` (letter 12) with stages 1–5 including
  this run's counts to a temp file and `os.replace` it into place; only
  then `next-stop`. NEXT after exit 0 is `status`.
- Unknown format at stage 3/5 produces an `unsupported-format` report under
  `data-map/unreadable.json` with evidence; no extractor code is generated
  at run time.

## Done when

```
python -m pytest -q tests/test_profiles.py tests/test_stage3_stage5.py
```

Covers: plan hash changes when the window changes; `next` outside the
window exits 20; unreachable host → diagnostic file, exactly one connect
attempt after the first, exit 20; stage 3 over the fake tree with the fake
LLM leaves every family interpreted or `unresolved` and the manifest
current; stage 5 plan refused when `next_profile` is absent or equals
`profile`; stage 5 next rejects a profile mapping an unknown extractor
name and otherwise writes `extractor-requests.json` and a `REPORT.md`
whose stage list includes 5 and whose hash `status` prints; `grep -r` of the
package finds no firewall, VPN, or approval-API client code.
