# Letter 00: Spike — ftp → LLM → markdown on one real equipment

## Goal

Run `spike.py` on one approved equipment through the office proxy until it
writes markdown, then record what happened. The script exists; this letter is
about running it at this site. Nothing else in this folder is needed until it
passes: read this letter, `equipment.toml.example`, and `spike.py` (170 lines,
read all of it), and skip `spec.md` and letters 01–20.

Pass means markdown from one real equipment. A fake tree running at home is
not a pass.

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
- **No exit-code contract, no `NEXT:` line, no per-item checkpoint.** One
  `progress.md` line at the end (step 6).
- Dependencies are stdlib, `ftp_handler/` (read-only, as in `AGENTS.md`), and
  `requests`. `pip install requests` if the import fails.

## Steps

1. **Proxy ready.** The engineer fills `.env` from `.env.example`. Then:

   ```
   python tests/test_ftp_transport.py
   python tests/check_proxy.py
   ```

   The first prints five `ok` lines. The second prints `no-token 401` then
   `token 200`. Any other pair means the proxy is not deployed or not enforcing
   its token: write the problem entry, append a `blocked` line, and stop.
   This step contacts the proxy only, never equipment.

2. **Config present.** The engineer copies `equipment.toml.example` to
   `equipment.toml` and fills it for one approved equipment with small roots
   and a small budget. Confirm shape without reading values:

   ```
   python -c "import tomllib; d = tomllib.load(open('equipment.toml', 'rb')); print(sorted(d), len(d['equipment']['roots']))"
   ```

   Expected: the four section names and a root count of at least 1.

3. **Run.**

   ```
   python spike.py equipment.toml
   ```

   The last line is one JSON object: `dirs`, `files`, `bytes`, `llm_calls`,
   `md`, and three booleans `index_exists`, `md_per_dir`, `evidence_tables`.
   Done here when all three booleans are true **and** `files > 0` **and**
   `llm_calls > 0`. Three true booleans over zero files means the walk saw no
   files; that is a failure, go to step 5.

4. **Read the output.** Open `out/<name>/index.md` and two directory files.
   Judge whether the `## LLM` section is usable: does `### Observed` stay
   within the evidence table, does `### Inferred` say something an engineer
   would keep? One or two sentences of judgement go into the problem entry.
   Read only from `out/`; never paste a directory file into a commit or
   `progress.md`.

5. **When it fails, fix `spike.py`, then rerun step 3.** The likely site
   differences: LLM reply not shaped as `choices[0].message.content`, an FTP
   server that rejects a command the library sends, a text encoding beyond
   UTF-8 and CP949, a listing format the library normalizes wrongly. Change
   `spike.py` only, keep it read-only (no upload, no path outside `roots`
   reaches the wire), and keep every change in a problem entry with the
   symptom and the diff summary. A fault inside `ftp_handler/` is a
   `blocked` line with the sanitized error, not an edit.

6. **Record.** Append one entry to `problems/00-problems.md` (format in
   `problems/README.md`) even on success: the JSON numbers from step 3, the
   judgement from step 4, where the letter or script stopped you, and the
   number of sessions used. Then one line to `progress.md`:

   ```
   - 00 done <UTC time> | dirs=<n> files=<n> bytes=<n> llm_calls=<n> | see problems/00-problems.md
   ```

   or `- 00 blocked ... | <one-line reason> | see problems/00-problems.md`.
   Commit only `spike.py`, `problems/00-problems.md` and `progress.md`
   (`git add` those three paths, `git diff --cached --stat` must list nothing
   else), message `letter 00: spike <done|blocked>`. `out/` and
   `equipment.toml` are ignored by git and stay on the PC.

## Done when

`python spike.py equipment.toml` on one approved equipment, through the
proxy, prints a last line whose three booleans are true with `files > 0` and
`llm_calls > 0`, and the `done` line is committed.

## What the script does

Reference for judging its output; the code is the source of truth.

- One `HostSpec` per call, `max_concurrency=1`, `passive=True`, transport
  from `fleet_downloader()`. The script never sets `FTP_TRANSPORT`.
- Walk: breadth-first from `roots`, one `size_dirs` per directory. A listing
  entry whose `SIZE` fails is treated as a subdirectory; a server with no
  `SIZE` at all makes every file look like one, and then file-named markdown
  appears. Report that, do not fix it here. `max_dirs` stops the walk and
  the index says how many directories were left.
- Sampling: newest file per extension per directory, by MDTM mtime. The
  whole file crosses the wire (the library has no range read), its full size
  counts against `max_download_bytes`, and only the first `sample_bytes` go
  to the LLM when they decode as UTF-8 or CP949.
- Evidence table `sample` column: `text head`, `meta only` (binary),
  `download failed`, `over budget`, `-` (not the newest of its extension).
  Denied files are absent from the table.
- One LLM call per non-empty directory, `POST <url>/v1/chat/completions`,
  Bearer header only when `api_key` is set. The heading records the alias
  you asked for and the `model` the endpoint answered with. HTTP 400/413
  becomes `input too large` in that file and the walk continues.
