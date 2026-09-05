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
- Header signature: read the first bytes of at most `header_files_per_family`
  files per pre-family, within the global header request budget. Split a
  pre-family when signatures disagree.
- Output table `families` in the sqlite: key, rule, member count, size
  stats, signature, exceptions (members that broke the rule and why).

## Done when

```
python -m pytest -q tests/test_grouping.py
```

Covers: the 100 date-varying logs form one family; a same-named file with a
different signature lands in a separate family or the exception list; header
reads never exceed the budgets; normalisation is a pure function with a
table of input→placeholder cases.
