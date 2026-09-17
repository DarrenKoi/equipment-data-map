# Letter 13: Equipment profiles, access window, stage 3 and 5

## Goal

What stage 3 and stage 5 need beyond stage 1: equipment profiles, the
access window in the plan hash, and connection diagnostics that stop
instead of retrying.

## Read

`spec.md` §8 stage 3 and stage 5, §4.4 (engineer inputs), §6.

## Build

Use implementation-reference.md §2 and §5 for the profile and window contract.

- `equipment_map/profiles.py`: profile registry file `profiles/<type>.json`
  with allowed path patterns, filename token rules, extractor mapping.
  `rollout.json` names a profile; grouping and extraction consult it.
- Access window: `always` or a UTC window, included in the canonical plan;
  `next` refuses to start outside the window (exit 20), checks before every
  equipment request and aborts in-flight work at its end. A returned timeout
  is not proof a worker or remote proxy stopped; test server-side termination.
- `stage 3 next`: the stage 1 pipeline against the real `Source` from
  `rollout.json` (`host`, `port`), then `interpret_families` from
  letter 11 over current-scope families without a matching durable field
  result (scope/input/model/prompt/glossary hashes must match), then
  `write_manifest`. Both halves run inside the letter 09 pass loop when
  `max_passes` > 1: later passes interpret only families whose input hash
  changed or that are still unresolved, with the letter 11 prior block. Connection failure writes a diagnostic file, one audit
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

Also run stages 1→2→3 on one rollout with fake and real-source fixtures
sharing paths but different bytes. Stage 3 must inventory and interpret the
new source with no old evidence in its manifest. Reconfigure stage 3 roots
and repeat; interrupt during scope activation and verify safe recovery.
Restart without reconfiguration must reuse completed current-scope work.

Pass loop (spec §7 pass bullets), with `max_passes` 3 over a fixture whose
frontier and unsampled families exceed one pass: kill at a pass boundary and
resume with no duplicate transfer or LLM request and no reset of pass number
or usage; exhausting eligible work ends `no-eligible-work`, the ceiling ends
`max-passes`, a small budget ends `budget`, each `completed: true`, exit 0,
`NEXT: equipment-map status`; permuting `confidence` values changes no
selection order; a changed linked-family Observed summary triggers one
re-interpretation while a changed prior alone triggers none.
