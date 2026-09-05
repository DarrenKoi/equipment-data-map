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
- repeated names group into one family
- format outliers are captured separately
- budget breach stops downloads immediately
- an over-budget file stays metadata-only with none of its bytes fetched
- the FTP transport follows the machine (Windows → proxy, else direct)
- resume from checkpoint after interruption
- encrypted and corrupt files survive as `unreadable`
- byte-identical `data-map/` on fixed input without LLM
- plan hash mismatch at run time stops
- concurrent run and unauthorised unlock are blocked
- next stage refused without previous approval
- next stage refused without result approval
- missing or wrong contract stops before any work
- fake SMB runs on a non-standard port

Where an existing test already proves a bullet, import or reuse it rather
than duplicating. Fix any gap found in the earlier modules; note the fix in
`progress.md`.

## Done when

```
python -m pytest -q
```

Whole suite green. `tests/test_scenarios_stage1.py` has exactly fifteen
test functions — one per §7 bullet. Recount §7 before you start: if the
spec has moved, the count moves with it.
