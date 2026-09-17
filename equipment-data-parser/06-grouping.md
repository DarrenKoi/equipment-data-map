# Letter 06: Grouping into file families

## Goal

Turn the inventory into file families by filename rule alone, before any LLM
and without downloading anything, with the rule recorded next to each family.

## Read

`spec.md` §4.3, §10 (100 files → at most 5 samples).

## Build

Use implementation-reference.md §5 for normalization, family kinds and IDs.

- `equipment_map/grouping.py`: filename normalisation replacing date, time,
  lot, wafer, recipe, and sequence tokens with placeholders, using the
  profile's token rules only.
- Two kinds of family, from metadata only:
  - `pattern`: two or more files sharing parent dir + normalised name +
    extension. These are files made in the same format over time or for
    related runs.
  - `loose`: every file with no such sibling, collected per parent dir +
    extension. A loose family claims no shared generation rule or format.
- No size buckets, no format signature, no content request of any kind.
  Grouping never calls the download guard. Merging or splitting families by
  format or content is out of scope until the whole map exists (spec §4.3);
  do not add it.
- Mark `active_candidate` members from metadata (newest, real-time, changing;
  spec §4.4) here, so sampling reads the flags instead of recomputing them.
- Output table `families` in the sqlite: `family_id`, kind, parent dir, name
  rule, extension, member count, size stats, mtime stats, and each member's
  normalized path, original name and matched token rules. `family_id` is the
  canonical hash from implementation-reference.md §5 within the current
  collection scope. Do not present it as a lifetime ID across changed scopes
  or profile rules.

## Done when

```
python -m pytest -q tests/test_grouping.py
```

Covers: the 100 date-varying logs form one `pattern` family; three unrelated
`.rcp` names in one directory form one `loose` family, while a lone `.ini` and
a lone `.xml` beside them form two one-member `loose` families; the same
normalised name with two extensions gives two families; a file whose name
shares no rule with a sibling never joins a `pattern` family; grouping sends
zero content requests (assert on the fake Source's call log); normalisation
is a pure function with a table of input→placeholder cases; `family_id` is
stable across two runs over the same inventory and changes when the scope
changes.
