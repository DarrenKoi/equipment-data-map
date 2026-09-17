# Letter 10: Stage 1 verification scenarios

## Goal

One test per spec §7 bullet that letters 01–09 can prove without an LLM, all
green. This is the gate that makes stage 1 releasable.

## Read

`spec.md` §7 (every bullet), §10.

## Build

`tests/test_scenarios_stage1.py`, one test function per bullet, named after
the bullet:

- no write operation exists
- repeated names group into one pattern family, other files into loose
  families by directory and extension, with zero content requests
- pattern families sample the latest three eligible plus two hash-ranked,
  loose families at most three, and a rerun picks the same files
- a pattern-family sample with a different extract format is an exception
- total byte target exhaustion stops the next download
- large and unknown-size eligible files download whole with actual usage recorded
- the FTP transport follows the machine (Windows → proxy, else direct)
- resume from checkpoint after interruption
- encrypted and corrupt files survive as `unreadable`
- byte-identical `data-map/` on fixed input without LLM
- deterministic observation IDs and new/changed/unchanged/missing state without
  upgrading unchanged to static
- bounded observed descriptors for every spec §4.7.2 category-shaped fixture,
  without copying full events/rows or inventing semantics
- plan hash mismatch at run time stops
- concurrent run and unauthorised unlock are blocked
- next stage refused without previous approval
- next stage refused without result approval
- missing or wrong contract stops before any work

Where an existing test proves a bullet, reference its test node in a coverage
table in `scenarios/README.md`; do not import test functions to inflate counts. Fix any gap found in the earlier modules; note the fix in
`office/progress.md`.

## Done when

```
python -m pytest -q
```

Whole suite green. Include the extra download-guard, growing-file,
collection-scope and metadata-evidence cases required by spec §7 in the
relevant earlier test modules. Maintain the coverage table against every current
§7 requirement; do not require an arbitrary number of test functions. Include
proxy authentication, stage/epoch/result-file integrity, deadline enforcement,
and output-injection cases added to the specification and implementation reference.
