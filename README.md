# Equipment Data Map

Company-internal kit for mapping FAB equipment file stores from metadata and
bounded representative samples. It produces an evidence-backed, Obsidian-readable Wiki
and graph material, and retains unknown or unreadable files explicitly.

**Current status:** documentation and a vendored FTP library. The extraction
CLI and portable skills are built in the office by the letters and never come
back by git. The office trial remains required; home checks do not establish
live-equipment readiness.

- **Office LLM:** start at [the office contract](equipment-data-parser/index.md),
  then follow its current letter; do not execute human gates.
- **Supervising engineer:** use [the handoff guide](equipment-data-parser/engineer-guide.md).
- **Implementation details:** [the reference](equipment-data-parser/implementation-reference.md)
  supplies concrete schemas, limits, prompts and acceptance behavior.
- **Maintainers:** follow [AGENTS.md](AGENTS.md) and the
  [authoritative architecture](docs/architecture/equipment-data-map.md).
- **Office ledger and problem reports:** the office agent writes them to `office/`
  in its model folder; they never come back by git ([format](equipment-data-parser/problems.md)).
- **Review:** see [the readiness review](docs/reviews/2026-09-10-office-guide.md)
  for corrected gaps, remaining dependencies and verification limits.

Home checks (no real equipment or credentials):

```sh
python3 tests/test_ftp_transport.py
python3 tests/test_sizing_mtime.py
python3 tests/test_worker_isolation.py
uv run --python 3.11 --with flask --with requests python tests/test_proxy_token.py
```

The checks replace external responses and inspect issued requests; none
contacts equipment. See the
[incremental improvement plan](docs/plans/2026-09-13-incremental-improvements.md)
for the home/office handoff and later expansion criteria.
