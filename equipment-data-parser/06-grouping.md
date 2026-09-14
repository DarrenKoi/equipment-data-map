# Letter 06: Grouping into file families

## Goal

Turn the inventory into file families by rule before any LLM, with the
rule and exceptions recorded next to each family.

## Read

`spec.md` §4.3, §4.4 header budgets, §10 (100 files → 3–5 samples).

## Build

Use implementation-reference.md §5 for normalization, size buckets and ties.

- `equipment_map/grouping.py`: filename normalisation replacing date, time,
  lot, wafer, recipe, and sequence tokens with placeholders; family key =
  parent dir + normalised name + extension + size bucket.
- Before any signature download, classify newest, real-time and changing
  candidates from metadata in each pre-family (spec §4.4). Both grouping and
  sampling call letter 03's shared download guard. Matching two inventories
  alone does not clear an active candidate; absent stability evidence, skip it.
- Format signature: there is no range read (spec §4.1), so the signature
  comes from normal whole-file downloads. Take at most
  `header_files_per_family` such files per pre-family, within the global
  header request budget, and read the signature off the leading bytes of
  what arrives. These whole-file transfers also consume global download
  files/time budgets and actual-byte accounting; keep them for sampling reuse.
  Per-file size is advisory, including for signatures. The shared guard still
  rejects denied or active candidates and stops new transfers after the total
  byte target is reached. Split a pre-family when signatures disagree. If no
  sample succeeds, retain `signature: none` with the actual no-sample reason.
- Output table `families` in the sqlite: key, rule, member count, size
  stats, signature, exceptions (members that broke the rule and why).
  `family_id` is the canonical hash of that family tuple within the current
  collection scope. Do not present it as a lifetime ID across changed scopes
  or profile rules.

## Done when

```
python -m pytest -q tests/test_grouping.py
```

Covers: the 100 date-varying logs form one family; a same-named file with a
different signature lands in a separate family or the exception list;
signature downloads respect candidate/count limits and account for whole-file
bytes, including overruns; denied or failed-only families yield `signature: none`
with their actual reasons; normalisation is a pure function
with a table of input→placeholder cases.

Also cover denied/newest/real-time/changing signature candidates with zero
content requests, aggregate budgets shared with sampling, and no eligible
member producing `signature: none` with explicit metadata-only reasons.
