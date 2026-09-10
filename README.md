# Equipment Data Map

Company-internal kit for mapping FAB equipment file stores from metadata and
bounded representative samples. It produces evidence-backed Wiki/RAG material
and retains unknown or unreadable files explicitly.

**Current status:** documentation and a vendored FTP library. The extraction CLI
and portable skills still need to be built and validated. No live-equipment
readiness is claimed.

- **Office LLM:** start at [the office contract](equipment-data-parser/index.md),
  then follow its current letter; do not execute human gates.
- **Supervising engineer:** use [the handoff guide](equipment-data-parser/engineer-guide.md).
- **Implementation details:** [the reference](equipment-data-parser/implementation-reference.md)
  supplies concrete schemas, limits, prompts and acceptance behavior.
- **Maintainers:** follow [AGENTS.md](AGENTS.md) and the
  [authoritative architecture](docs/architecture/equipment-data-map.md).
- **Office problem reports:** use the root [problems/](problems/README.md) folder.
- **Review:** see [the readiness review](docs/reviews/2026-09-10-office-guide.md)
  for corrected gaps, remaining dependencies and verification limits.

The existing local check is `python3 tests/test_ftp_transport.py`. It checks
transport selection only; it does not validate file extraction or an office proxy.
