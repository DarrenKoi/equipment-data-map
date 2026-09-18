# Letter 21: Extractor release

## Goal

Promote one workbench method the engineer has proven on a real sample into
a tested extractor module: the separate reviewed CLI release that spec §4.5
requires before a format leaves `unsupported-format`. One run of this letter
is one release, named by the engineer in `engineer.toml`:

```toml
[release]
id = "<opaque id>"          # same form as a rollout id
workbench = "<copy dir>"    # the workbench copy that holds attempts.jsonl
result_sha256 = "<64 hex>"  # the successful attempt to promote
extractor = "<name>"        # the new extractor's name
```

## Read

`spec.md` §4.5 (Extractor workbench). implementation-reference.md §5
(registry names, `extractor_mapping`) and §6 (limits and output).

From the workbench copy read `attempts.jsonl` only: method names, options
and hashes. The copied sample is the engineer's; you never open or list it,
and nothing in a fixture comes from it.

## Build

1. Find the attempt whose `result_sha256` equals the one in `[release]`.
   When none matches, when its method is `hermes-gui` (a GUI session cannot
   run inside an autonomous stage, so it never becomes an extractor), or
   when `extractor` is not a free registry name, append `blocked` and a
   problem entry, and stop. The engineer corrects `[release]`.
2. `equipment_map/extract/<extractor>.py`: runs the attempt's method with
   its `method_config` fixed in code, under the letter 08 limits. Its
   result must be byte-identical to that method's, because the engineer's
   check below compares the two hashes. Register the name so profile
   `extractor_mapping`, the stage 5 extractor check and `workbench --method`
   accept it. The magic-bytes and extension dispatcher stays unchanged: the
   new extractor runs only where a profile maps it.
3. `tests/test_extract_<extractor>.py` with a synthetic fixture built from
   `method_config` alone (the encoding, delimiter or layout it names). On the
   fixture, the new module and the attempt's method with its options give
   the same result bytes and the same `result_sha256`; the same input twice
   gives byte-identical output; the letter 08 limits hold; a profile mapping
   an extension to the new name validates.
4. Bump the minor `version` in `pyproject.toml` and reinstall with the
   letter 01 pip line. `SUPPORTED_CONTRACTS` stays as it is: an extractor
   changes no command, exit code or `NEXT:` line.

## Done when

```
python -m pytest -q
```

Whole suite green. Then append `waiting` for the engineer to run
`equipment-map workbench` with `--method <extractor>` on the same copy, with
this match check, which exits 0 once the newest attempt reproduces the
promoted result:

```sh
python -c "import json,tomllib; t=tomllib.load(open('engineer.toml','rb'))['release']; r=[json.loads(l) for l in open(t['workbench']+'/attempts.jsonl',encoding='utf-8') if l.strip()][-1]; raise SystemExit(r['method']!=t['extractor'] or r['result_sha256']!=t['result_sha256'])"
```

That match is the review: the module reproduces the proven result on the
real sample without the sample reaching you. Record the extractor name and
the new CLI version in the `done` line. The release changes the CLI code, so
the next rollout cannot adopt a baseline and runs stages 1 and 2 again
(spec §5).
