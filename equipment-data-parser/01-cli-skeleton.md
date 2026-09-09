# Letter 01: CLI skeleton and exit contract

## Goal

An installable `equipment-map` command whose every exit obeys the fixed exit
code and `NEXT:` contract, with a working `preflight` and an empty `status`.

## Read

`spec.md` §5 (commands, exit codes, stdout rules), §9 bullet on `--contract`.

## Build

- `pyproject.toml` with the console script and dev extras (`pytest`).
  Install it with pip, never uv: `python -m pip install -e ".[dev]"`.
  Record that exact line in `progress.md`; every later letter's
  **Done when** assumes this editable install is in place.
- `equipment_map/cli.py`: argparse with subcommands `init`, `preflight`,
  `stage <N> plan`, `stage <N> next`, `status`, `operator approve-plan`,
  `operator approve-result`, `operator unlock`. All but `preflight` and
  `status` may raise `NotImplementedError` for now.
- `equipment_map/exit.py`: one `finish(code, next_line)` that prints
  `NEXT: <...>` as the final stdout line and returns the code. Codes are the
  four in spec §5 and nothing else.
- `preflight --stage N --contract V`: exit 0 with `NEXT: equipment-map status`
  when `V` is in `SUPPORTED_CONTRACTS` (start with `["1"]`), else exit 30 with
  `NEXT: INSTALL-OR-UPGRADE` and an install hint.
  Contract check only — no network call. Letter 03 adds the transport check
  to this same subcommand.
- `status` with no `--rollout`: list rollout ids under `./rollouts/` (empty
  list is fine), exit 0.
- `--rollouts-dir` global option defaulting to `./rollouts`, so tests can use
  a temp dir.

## Done when

```
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_cli_contract.py
```

That file covers: each subcommand's last stdout line starts with `NEXT: `;
`preflight` returns 0 and 30 for supported and unsupported contracts;
`status` on an empty dir returns 0; any uncaught exception maps to exit 20
and `NEXT: STOP`.
