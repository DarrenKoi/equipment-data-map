# Letter 00: Spike — ftp → LLM → markdown on one real equipment

## Goal

Use `spike.py` on one approved equipment through the office proxy to produce
a first-pass map of its file structure with one engineer-configured small
local model, then record what happened. The script exists; this letter is
about running it at this site. Nothing else in this folder is needed until it
passes: read this letter, `equipment.toml.example`, and all of `spike.py`,
and skip `spec.md` and letters 01–20.

Pass means markdown from one real equipment. A fake tree running at home is
not a pass.

Prioritize directory paths, file metadata (names, extensions, sizes and
modification times), and observed facts from limited samples. The LLM records
only what one directory's listing and samples show; it states no purpose for
the directory, because one folder cannot reveal how the tool works. Inference
comes in a later pass, from observed facts across directories. Do not attempt complete
content extraction, cross-folder relationship analysis, or multi-model
orchestration. Possible relationships remain unverified observations for a
later investigation; they do not trigger more collection in this pass.

Report inventory, sampling and interpretation coverage separately, including
exclusions, listing failures, skipped samples, failed LLM calls and budget
stops visible in the output. If an exact count or unexplored scope is not
available, record it as unknown; do not invent a complete coverage figure.
Keep the map in `out/`, outside this read-only instruction folder.
After recording the checkpoint, stop for engineer review even on success.
Do not start letters 01–20 or rerun a completed pass without an explicit request.

## Where this letter overrides index.md

- **Equipment facts live in `equipment.toml`**, filled by the engineer and
  read only by `spike.py`. There is no `init`, no keystore, no alias. You
  never open that file: no `cat`, no Read, no `python -c` that prints a value
  from it. Step 2 shows the one inspection that is allowed.
- **Paths may appear on stdout and in `out/`.** The office network has no
  external egress, which replaces the stdout path rule. `password` and
  `api_key` still appear nowhere: `spike.py` scrubs them from every file it
  writes and from its own output, and exception text is reduced to a class
  name. Keep that property in any edit you make.
- **No staged CLI exit-code contract, no `NEXT:` line, no per-item checkpoint.**
  The spike uses the 0/1 smoke-check verdict in step 3 and one `office/progress.md`
  line at the end (step 6).
- Dependencies are stdlib, `ftp_handler/` (read-only, as in `AGENTS.md`), and
  `requests`. `pip install requests` if the import fails.

## Steps

1. **Proxy ready.** The engineer fills `.env` from `.env.example`. Then:

   ```
   python tests/test_ftp_transport.py
   python tests/check_proxy.py
   ```

   The first prints five `ok` lines. The second prints `no-token 200` when
   `FTP_PROXY_TOKEN` is empty (trusted no-auth proxy), or `no-token 401` then
   `token 200` when it is set. Any other output means the proxy is not
   deployed, or does not match the token setting in `.env`: write the problem
   entry, append a `blocked` line, and stop.
   This step contacts the proxy only, never equipment.

2. **Config present.** The engineer copies `equipment.toml.example` to
   `equipment.toml` and fills it for one approved equipment with small roots
   and a small budget. Select an approved small local model for preliminary
   directory descriptions; model size does not prove accuracy. Confirm shape
   without reading values:

   ```
   python -c "import tomllib; d = tomllib.load(open('equipment.toml', 'rb')); print(sorted(d), len(d['equipment']['roots']))"
   ```

   Expected: the four section names and a root count of at least 1.

3. **Run.**

   ```
   python spike.py equipment.toml
   ```

   Once step 5 has created `office/spike.py`, run that copy instead:
   `PYTHONPATH=. python office/spike.py equipment.toml`.

   The last line is one JSON object containing:

   - `dirs`, `files`, `md`, and `output_dir` for this invocation.
   - `bytes`: actual bytes of successfully received whole files;
     `estimated_bytes`: listed sizes of attempted downloads;
     `overrun_bytes`: successful bytes above `max_download_bytes`.
   - `download_failed` and `usage_unknown`: failed transfers can consume
     unreported partial bytes. When usage is unknown, no further download
     starts during this invocation. Do not treat `bytes` as all network traffic.
   - `llm_calls` (attempts), `llm_success` (valid response shape), `llm_failed`.
   - `index_exists`, `md_per_dir`, `evidence_tables`.

   Exit 0 requires all three booleans, `files > 0`, `llm_success > 0`,
   and `usage_unknown == false`. Otherwise exit 1; go to step 5. These checks
   do not prove complete inventory or accurate interpretation. Review any
   failed LLM calls and skipped samples even when the exit code is 0.

4. **Read the output.** Open `<output_dir>/index.md` using the path in the
   final JSON, then follow its links to two directory files (or all if fewer).
   Each invocation writes a fresh `out/<name>/<run-id>/`; directory filenames
   use path hashes, and previous output is preserved. This is not checkpoint
   resume: a new invocation starts a new budget and walks the roots again.
   Judge whether the `## LLM` section is usable: does `### Observed` stay
   within the evidence table and samples, and does it record facts an engineer
   would keep (naming patterns, formats, visible fields) without guessing the
   directory's purpose? Format validation does not establish factual accuracy.
   One or two sentences of judgement go into the problem entry. An unusable
   analysis is not a pass, even with exit 0.
   Read only from `out/`; never paste a directory file into a commit or
   `office/progress.md`.

5. **When it fails, fix `office/spike.py`, then rerun step 3.** If `usage_unknown`
   is true, first stop and ask the engineer to verify the previous transfer
   has ended and reconcile its usage before authorizing a new invocation.
   A new output directory does not settle unknown usage. The likely site
   differences: LLM reply not shaped as `choices[0].message.content`, an FTP
   server that rejects a command the library sends, a text encoding beyond
   UTF-8 and CP949, a listing format the library normalizes wrongly. The
   root `spike.py` is the maintainer's: the first time you need a change,
   `cp spike.py office/spike.py` and edit only the copy. Keep it read-only (no upload, no path outside `roots`
   reaches the wire), and keep every change in a problem entry with the
   symptom and the diff summary. A fault inside `ftp_handler/` is a
   `blocked` line with the sanitized error, not an edit.

   **For a timeout, identify the failing layer before editing.** Record the
   exception class or HTTP status without credentials: an LLM failure in a
   directory report, an FTP/proxy failure, or an agent/terminal run limit.
   `llm.timeout_s` controls each LLM HTTP request, not the total walk or FTP
   calls; its default is 60 seconds. Each non-empty directory sends its full
   evidence table plus sampled heads, so large listings can make requests
   slow. A report containing `call failed: ReadTimeout` retains that
   directory's evidence and the script continues; it is failed interpretation,
   not proof the directory could not be inventoried.
   For a confirmed slow LLM request, the engineer may set a longer finite
   `llm.timeout_s` in the private config. This does not resolve context-size
   rejection, FTP/proxy timeouts or a runner terminating the whole process.
   Do not automatically retry the whole walk or increase collection budgets.
   If the runner interrupted a transfer, verify it has ended and reconcile
   usage before another invocation. Preserve partial output; the spike has no
   checkpoint resume and may lack `index.md` if interrupted before completion.

   **Known office runner limit: 30 minutes.** With `llm.timeout_s = 300`,
   six requests waiting about five minutes each already consume that window,
   before FTP work. `spike.py` makes one request per non-empty directory
   and has no LLM retry loop. While `office/spike.py` does not exist, the root
   script is what ran, so repeated waits are not script retries: they come
   from the serving layer (gateway queueing or retries) or from the runner
   relaunching the command. Record which one; a retry loop is not the fix. Its final JSON and
   `index.md` are written only after the walk, so no final print at the runner
   limit is not evidence of an LLM failure or a completed run.
   Before another launch, have the engineer check whether the old process is
   still running; a tool timeout does not establish that it was terminated.
   If it is still running, do not start a duplicate. For a new authorized run,
   use the tool's documented persistent-process support if available, or have
   the engineer run the command in a separate terminal that can remain open
   beyond 30 minutes. Follow the same process to completion; do not restart
   the walk at every tool timeout. Keep existing roots and collection budgets.
   In a non-interactive session without such process support, record the
   runner limitation and stop for the engineer rather than launching a job
   whose lifetime cannot be tracked. A longer LLM timeout or unbuffered Python
   output alone does not fix this runner limit.

6. **Record.** Append one entry to `office/problems/00-problems.md` (format in
   `problems.md`) even on success: the JSON numbers from step 3, the
   judgement from step 4, where the letter or script stopped you, and the
   number of sessions used. Then one line to `office/progress.md`:

   ```
   - 00 done <UTC time> | dirs=<n> files=<n> bytes=<n> llm_success=<n> llm_failed=<n> | see office/problems/00-problems.md
   ```

   or `- 00 blocked ... | <one-line reason> | see office/problems/00-problems.md`.
   Commit on the local office branch only `office/` (`git add -- office/`;
   `git diff --cached --stat` must list nothing outside it), message `letter 00: spike <done|blocked>`. `out/` and
   `equipment.toml` are ignored by git and stay on the PC.

## Done when

`python spike.py equipment.toml` on one approved equipment, through the
proxy, exits 0 with three true booleans, `files > 0`, `llm_success > 0` and
`usage_unknown == false`. The engineer judges the analysis usable, and the
`done` line is committed. Home fake tests never complete this letter.

## What the script does

Reference for judging its output; the code is the source of truth.

- One `HostSpec` per call, `max_concurrency=1`, `passive=True`, transport
  from `fleet_downloader()`. The script never sets `FTP_TRANSPORT`.
- Walk: breadth-first from deduplicated, normalized `roots`. First use
  `list_dirs`, check normalized paths against roots and deny patterns, then
  use `size_dirs` with fixed accepted paths only (no listing expansion).
  Check download candidates again before calling `download`. This avoids
  SIZE/MDTM as well as RETR on excluded entries without changing the vendored
  library. The extra listing connection is intentional. A listing
  entry whose `SIZE` fails is treated as a subdirectory; a server with no
  `SIZE` at all makes every file look like one, and then file-named markdown
  appears. Report that, do not fix it here. `max_dirs` stops the walk and
  the index says how many directories were left.
- Sampling: newest file per extension per directory, by MDTM mtime. The
  whole file crosses the wire (the library has no range read). Download one
  file at a time and count its actual received length. Listed size is advisory:
  a file larger than the remaining target can still be received whole. Once
  successful bytes reach `max_download_bytes`, no next download starts.
  This is a best-effort total target, not an in-flight cap. Only the first
  `sample_bytes` go to the LLM when they decode as UTF-8 or CP949.
- Evidence table `sample` column: `text head`, `meta only` (binary),
  `download failed, usage unknown`, `usage unknown, skipped`, `over budget`,
  `-` (not the newest of its extension).
  Denied files are absent from the table. Besides `deny`, the script always
  excludes site noise: `NOISE_EXTENSIONS` (`.bak`, `.iso`, `.lock`) and
  `NOISE_WORDS` (`temp`, `tmp` as a word no letter touches, so
  `temperature.log` stays), case-insensitive, on any path segment below a
  root. The maintainer extends those lists; a missing noise pattern here is a
  problem entry, not a `deny` workaround hidden in the private config.
- One LLM call per non-empty directory, `POST <url>/v1/chat/completions`,
  Bearer header only when `api_key` is set. The heading records the alias
  you asked for and the `model` the endpoint answered with. HTTP 400/413
  becomes `request rejected` in that file and the walk continues. A successful
  HTTP response counts as `llm_success` only if its content is exactly one
  non-empty `### Observed` section; any other `###` section, such as a guessed
  `### Inferred`, makes it invalid.
