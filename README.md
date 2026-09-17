# Equipment Data Map

Company-internal kit for mapping FAB equipment file stores from metadata and
bounded representative samples. It produces an evidence-backed, Obsidian-readable Wiki
and graph material, and retains unknown or unreadable files explicitly.

**Current status:** documentation, a vendored FTP library, and `spike.py` for
FTP → optional LLM → Markdown on one equipment. The extraction CLI and portable skills
still need to be built and validated. The office trial remains required;
home checks do not establish live-equipment readiness.

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
python3 tests/test_spike_boundaries.py
uv run --python 3.11 --with pyftpdlib --with flask --with requests python tests/test_spike_fake.py
uv run --python 3.11 --with pyftpdlib --with flask --with requests python tests/test_spike_fake.py direct
```

The boundary checks replace external responses and inspect issued requests.
The last two commands run a local fake FTP server and fake LLM, using the real
proxy or direct transport. `pyftpdlib` is a test-server dependency only; office
equipment supplies its own FTP server. Local loopback listeners must be allowed.

Each spike invocation writes `out/<name>/<UTC time>/`, one `index.md` per
directory in the equipment's own folder layout, linked from its parent. The final JSON identifies `output_dir`, actual successful download
bytes, overrun and unknown usage, and LLM attempts/successes/failures. A successful
exit is a smoke check; an engineer still reviews coverage and interpretation.
See the [incremental improvement plan](docs/plans/2026-09-13-incremental-improvements.md)
for the home/office handoff and later expansion criteria.
