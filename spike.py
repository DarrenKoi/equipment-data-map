"""ftp -> LLM -> markdown spike for one equipment. ``python spike.py equipment.toml``.

Walks the configured roots read-only, samples the newest file per extension in
each directory, asks the office LLM once per directory, and writes one markdown
per directory plus ``index.md``. Ends with a three-condition self-check.
Letter: equipment-data-parser/00-spike.md.
"""

import fnmatch
import json
import posixpath
import sys
import tomllib
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import requests

from ftp_handler import fleet_downloader
from ftp_handler.direct_downloader import HostSpec, ListDir

PROMPT = (
    "You describe one directory of a FAB equipment file store from partial evidence. "
    "Reply in markdown with exactly two sections: '### Observed' (only what the "
    "listing and samples show) and '### Inferred' (what the directory is probably "
    "for, marked as a guess). Be brief."
)


def main(config_path):
    cfg = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    eq, budget, llm = cfg["equipment"], cfg["budget"], cfg["llm"]
    secrets = [s for s in (eq.get("password"), llm.get("api_key")) if s]

    def scrub(text):  # rule: secrets never reach stdout or any output file
        for s in secrets:
            text = text.replace(s, "***")
        return text

    roots = [posixpath.normpath(r) for r in eq["roots"]]

    def inside(path):
        p = posixpath.normpath(path)
        return any(p == r or p.startswith(r + "/") for r in roots)

    def denied(path):  # deny patterns match the path relative to its root, or the basename
        root = next((r for r in roots if path == r or path.startswith(r + "/")), "/")
        rel, base = posixpath.relpath(path, root), posixpath.basename(path)
        return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(base, p) for p in eq.get("deny", []))

    dl = fleet_downloader()(
        user=eq["user"], password=eq["password"], port=eq.get("port", 21),
        max_concurrency=1, passive=True,
    )
    spec = lambda **kw: HostSpec(eq["host"], **kw)  # one host, the fleet of one

    out = Path(cfg.get("output", {}).get("dir", "out")) / eq["name"]
    out.mkdir(parents=True, exist_ok=True)
    stats = {"dirs": 0, "files": 0, "bytes": 0, "llm_calls": 0, "md": 0}
    index = ["# " + eq["name"], "", "| directory | files | note |", "|---|---|---|"]
    queue, seen = deque(roots), set(roots)

    while queue and stats["dirs"] < budget["max_dirs"]:
        d = queue.popleft()
        if not inside(d):  # allowlist: refused before it reaches the wire
            index.append(f"| {d} | - | outside roots, skipped |")
            continue
        stats["dirs"] += 1
        report = dl.size_dirs([spec(listings=[ListDir(d)])])
        note = ""
        for f in report.failures:
            if f.remote_path in (None, d):
                note = "listing failed: " + f.error.split(":")[0]
            elif f.remote_path not in seen and not denied(f.remote_path):
                # ponytail: SIZE fails on a directory, so a failed SIZE is the
                # subdirectory signal. A server without SIZE at all makes every
                # file look like a directory; then every "child" lists only
                # itself and yields an empty md. Live with it for the spike.
                seen.add(f.remote_path)
                queue.append(f.remote_path)
        files = [f for f in report.files if not denied(f.remote_path)]
        stats["files"] += len(files)

        # newest file per extension, one download batch per directory
        newest = {}
        for f in files:
            ext = posixpath.splitext(f.remote_path)[1].lower()
            key = f.modified or datetime.min.replace(tzinfo=timezone.utc)
            if ext not in newest or key > newest[ext][0]:
                newest[ext] = (key, f)
        wanted, verdict = [], {}
        for _, f in newest.values():
            if stats["bytes"] + f.size > budget["max_download_bytes"]:
                verdict[f.remote_path] = "over budget"
            else:
                stats["bytes"] += f.size  # whole file crosses the wire, no range read
                wanted.append(f.remote_path)
        got = dl.download([spec(files=wanted)]) if wanted else None
        samples = {}
        for r in (got.files if got else []):
            head = r.data[: budget["sample_bytes"]]
            text = decode(head)
            samples[r.remote_path] = text
            verdict[r.remote_path] = "text head" if text is not None else "meta only"
        for x in (got.failures if got else []):
            verdict[x.remote_path or "?"] = "download failed"

        rows = ["| file | ext | size | mtime | sample |", "|---|---|---|---|---|"]
        for f in sorted(files, key=lambda f: f.remote_path):
            when = f.modified.isoformat() if f.modified else "unknown"
            rows.append(f"| {posixpath.basename(f.remote_path)} | {posixpath.splitext(f.remote_path)[1].lower() or '-'} "
                        f"| {f.size} | {when} | {verdict.get(f.remote_path, '-')} |")
        description = ask_llm(llm, d, rows, samples) if files else "(empty directory, LLM not called)"
        stats["llm_calls"] += bool(files)

        md = "\n".join([f"# {d}", "", "## Evidence", ""] + rows + ["", description, ""])
        name = d.strip("/").replace("/", "__") or "root"
        (out / f"{name}.md").write_text(scrub(md), encoding="utf-8")
        stats["md"] += 1
        index.append(f"| [{d}]({name}.md) | {len(files)} | {note} |")

    if queue:
        index.append(f"| ... | - | max_dirs reached, {len(queue)} directories not visited |")
    (out / "index.md").write_text(scrub("\n".join(index) + "\n"), encoding="utf-8")

    checks = {
        "index_exists": (out / "index.md").exists(),
        "md_per_dir": stats["md"] == stats["dirs"],
        "evidence_tables": sum("## Evidence" in p.read_text(encoding="utf-8")
                               for p in out.glob("*.md") if p.name != "index.md") == stats["dirs"],
    }
    print(scrub(json.dumps({**stats, **checks})))
    return 0 if all(checks.values()) else 1


def decode(head):
    for enc in ("utf-8", "cp949"):
        try:
            return head.decode(enc)
        except UnicodeDecodeError:
            pass
    return None


def ask_llm(llm, d, rows, samples):
    parts = [f"Directory: {d}", "", "Listing:", *rows, ""]
    for path, text in samples.items():
        parts += [f"--- {posixpath.basename(path)} (first bytes) ---",
                  text if text is not None else "(binary, not shown)", ""]
    headers = {"Authorization": f"Bearer {llm['api_key']}"} if llm.get("api_key") else {}
    body = {"model": llm["model"],
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": "\n".join(parts)}]}
    try:
        resp = requests.post(llm["url"].rstrip("/") + "/v1/chat/completions",
                             json=body, headers=headers, timeout=llm.get("timeout_s", 60))
        if resp.status_code in (400, 413):
            return f"## LLM\n\ninput too large (HTTP {resp.status_code})"
        resp.raise_for_status()
        data = resp.json()
        served = data.get("model", "?")
        return f"## LLM ({llm['model']} -> {served})\n\n{data['choices'][0]['message']['content']}"
    except Exception as exc:  # noqa: BLE001 - class name only, no URL or key
        return f"## LLM\n\ncall failed: {type(exc).__name__}"


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "equipment.toml"))
