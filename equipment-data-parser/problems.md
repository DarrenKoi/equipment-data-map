# Problems

Problem entries live in the repository-root `office/problems/` folder on the
office branch. The office-agent contract and progress format are in
[index.md](index.md).

One file per letter, `office/problems/NN-problems.md` (`16-problems.md` for letter 16), created
the first time that letter meets something the letters did not anticipate:
this office's network, PC image, credentials, FTP behaviour, equipment
directory habits, file formats, the local LLM endpoint, or an instruction that
turns out to be wrong or impossible here.

The letters were written without knowledge of this office and these FAB tools.
They are a plan, not a description of your site. When reality differs, the
difference is the deliverable of this folder — the engineer reads it to decide
what to change, and the next session reads it instead of rediscovering it.

## Rules

- Append only. Never edit or delete an earlier entry; add a new one that
  supersedes it and say so.
- Write the entry when you hit the problem, not at the end of the letter.
- Commit it with the build item it came from, message
  `letter NN: problem — <short title>`, on the local office branch. It
  never leaves this PC by git; the engineer relays a sanitized summary to the
  maintainer.
- A problem file is **not** a substitute for `office/progress.md`. If the problem
  stops you, still append the `blocked` (or `waiting`) line to `office/progress.md`
  and point at the entry: `... | see office/problems/NN-problems.md`.
- Facts only: safe command templates, exit/status codes and sanitized errors. No guessing at
  causes you did not verify, no equipment addresses, paths, or credentials —
  describe them (`the tool's log root`, `the shared read-only account`).
  Never paste raw transport exceptions, requests, or model responses. Detailed
  diagnostics stay in access-controlled local runtime files for the engineer;
  refer to a diagnostic id only. Do not commit them with this report.
- Do not fix the letters yourself. Record the problem and the workaround you
  used; changing a letter is the engineer's call.

## Correction rounds

Use the same per-letter file across repeated sessions. After a maintainer fix
or engineer decision, append a follow-up identifying the earlier entry, the
instruction/code revision, the check actually run and whether the blocker is
resolved or still open. Keep details sanitized. Update `office/progress.md` separately
with the next checkpoint or remaining blocker; a problem resolution is not a
letter completion or an equipment approval.

## Entry format

```markdown
## <UTC date> — <short title>

- **Step:** letter NN, build item <n> / operating step <n>
- **Expected:** what the letter or spec assumed would happen
- **Observed:** what actually happened, with the command and its output
- **Cause:** verified cause, or `unknown`
- **Workaround:** what you did to continue, or `none — blocked`
- **Needs engineer:** yes/no — the decision or access required
```
