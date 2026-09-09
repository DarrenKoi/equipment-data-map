# Letter 06: Grouping into file families

## Goal

Turn the inventory into file families by rule before any LLM, with the
rule and exceptions recorded next to each family.

## Read

`spec.md` §4.3, §4.4 header budgets, §10 (100 files → 3–5 samples).

## Build

- `equipment_map/grouping.py`: filename normalisation replacing date, time,
  lot, wafer, recipe, and sequence tokens with placeholders; family key =
  parent dir + normalised name + extension + size bucket.
- Before any signature download, classify newest, real-time and changing
  candidates from metadata in each pre-family (spec §4.4). Both grouping and
  sampling call letter 03's shared download guard. Matching two inventories
  alone does not clear an active candidate; absent stability evidence, skip it.
- Format signature: there is no range read (spec §4.1), so the signature
  comes from whole files that fit the per-file byte budget. Take at most
  `header_files_per_family` such files per pre-family, within the global
  header request budget, and read the signature off the leading bytes of
  what arrives. These whole-file transfers also consume global download
  files/bytes/time budgets; keep them for sampling reuse. Files over the
  budget or rejected by the shared guard are never fetched for a signature.
  Split a pre-family when signatures disagree. When every member of a
  pre-family is over budget, keep it grouped on path, extension, and size
  alone, and record `signature: none` with reason `oversize` so the family
  is not mistaken for one that was actually inspected.
- Output table `families` in the sqlite: key, rule, member count, size
  stats, signature, exceptions (members that broke the rule and why).

## Done when

```
python -m pytest -q tests/test_grouping.py
```

Covers: the 100 date-varying logs form one family; a same-named file with a
different signature lands in a separate family or the exception list;
signature reads never exceed the budgets and never fetch an over-budget
file; an all-oversize pre-family yields `signature: none` with reason
`oversize` rather than an unread guess; normalisation is a pure function
with a table of input→placeholder cases.

Also cover denied/newest/real-time/changing signature candidates with zero
content requests, aggregate budgets shared with sampling, and no eligible
member producing `signature: none` with explicit metadata-only reasons.
