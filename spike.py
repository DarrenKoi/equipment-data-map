"""ftp -> LLM -> markdown spike for one equipment. ``python spike.py equipment.toml``.

Walks the configured roots read-only, samples the newest file per extension in
each directory, asks the office LLM once per directory, and writes one markdown
per directory plus ``index.md``. Ends with a three-condition self-check.
Letter: equipment-data-parser/00-spike.md.
"""

import fnmatch
import hashlib
import json
import posixpath
import re
import sys
import tomllib
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests

from ftp_handler import fleet_downloader
from ftp_handler.direct_downloader import HostSpec, ListDir
from ftp_handler.direct_downloader.fleet_downloader import SizingReport

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

    roots = list(dict.fromkeys(posixpath.normpath(r) for r in eq["roots"]))

    def inside(path):
        p = posixpath.normpath(path)
        return any(p == r or p.startswith(r.rstrip("/") + "/") for r in roots)

    def denied(path):  # deny patterns match the path relative to its root, or the basename
        base = posixpath.basename(path)
        return any(fnmatch.fnmatch(base, pattern) or
                   any(fnmatch.fnmatch(posixpath.relpath(path, root), pattern)
                       for root in roots if path == root or path.startswith(root.rstrip("/") + "/"))
                   for pattern in eq.get("deny", []))

    def allowed(path):
        return inside(path) and not denied(posixpath.normpath(path))

    dl = fleet_downloader()(
        user=eq["user"], password=eq["password"], port=eq.get("port", 21),
        max_concurrency=1, passive=True,
    )
    spec = lambda **kw: HostSpec(eq["host"], **kw)  # one host, the fleet of one

    out = Path(cfg.get("output", {}).get("dir", "out")) / eq["name"] / uuid4().hex
    out.mkdir(parents=True, exist_ok=False)
    stats = {"dirs": 0, "files": 0, "bytes": 0, "estimated_bytes": 0,
             "overrun_bytes": 0, "download_failed": 0, "usage_unknown": False,
             "llm_calls": 0, "llm_success": 0, "llm_failed": 0, "md": 0}
    index = ["# " + eq["name"], "", "| directory | files | note |", "|---|---|---|"]
    queue, seen = deque(roots), set(roots)

    while queue and stats["dirs"] < budget["max_dirs"]:
        d = queue.popleft()
        if not allowed(d):  # policy applies to configured roots too
            index.append(f"| {d} | - | excluded by path policy |")
            continue
        stats["dirs"] += 1
        listing = dl.list_dirs([spec(listings=[ListDir(d)])])
        paths = sorted({posixpath.normpath(p) for item in listing.listings for p in item.paths
                        if allowed(p) and posixpath.normpath(p) != d})
        # Fixed paths prevent SIZE/MDTM on unchecked server listing entries.
        report = dl.size_dirs([spec(files=paths)]) if paths else SizingReport([], [])
        note = ""
        for f in [*listing.failures, *report.failures]:
            if f.remote_path in (None, d):
                note = "listing failed: " + f.error.split(":")[0]
            elif f.remote_path in paths and f.remote_path not in seen and allowed(f.remote_path):
                # ponytail: SIZE fails on a directory, so a failed SIZE is the
                # subdirectory signal. A server without SIZE at all makes every
                # file look like a directory; then every "child" lists only
                # itself and yields an empty md. Live with it for the spike.
                seen.add(f.remote_path)
                queue.append(f.remote_path)
        files = [f for f in report.files if f.remote_path in paths and allowed(f.remote_path)]
        stats["files"] += len(files)

        # Newest file per extension; each completed transfer gates the next.
        newest = {}
        for f in files:
            ext = posixpath.splitext(f.remote_path)[1].lower()
            key = f.modified or datetime.min.replace(tzinfo=timezone.utc)
            if ext not in newest or key > newest[ext][0]:
                newest[ext] = (key, f)
        samples, verdict = {}, {}
        for _, f in newest.values():
            if stats["usage_unknown"]:
                verdict[f.remote_path] = "usage unknown, skipped"
                continue
            if stats["bytes"] >= budget["max_download_bytes"]:
                verdict[f.remote_path] = "over budget"
                continue
            if not allowed(f.remote_path):
                continue
            stats["estimated_bytes"] += f.size
            got = dl.download([spec(files=[f.remote_path])])
            if got.failures or len(got.files) != 1 or got.files[0].remote_path != f.remote_path:
                # ponytail: the vendor cannot report partial failure bytes. Stop
                # new transfers; a future resume ledger must reconcile this usage.
                stats["download_failed"] += 1
                stats["usage_unknown"] = True
                verdict[f.remote_path] = "download failed, usage unknown"
                continue
            r = got.files[0]
            stats["bytes"] += len(r.data)
            stats["overrun_bytes"] = max(0, stats["bytes"] - budget["max_download_bytes"])
            head = r.data[: budget["sample_bytes"]]
            text = decode(head)
            samples[r.remote_path] = text
            verdict[r.remote_path] = "text head" if text is not None else "meta only"

        rows = ["| file | ext | size | mtime | sample |", "|---|---|---|---|---|"]
        for f in sorted(files, key=lambda f: f.remote_path):
            when = f.modified.isoformat() if f.modified else "unknown"
            rows.append(f"| {posixpath.basename(f.remote_path)} | {posixpath.splitext(f.remote_path)[1].lower() or '-'} "
                        f"| {f.size} | {when} | {verdict.get(f.remote_path, '-')} |")
        description = "(empty directory, LLM not called)"
        if files:
            description, valid = ask_llm(llm, d, rows, samples)
            stats["llm_calls"] += 1
            stats["llm_success"] += valid
            stats["llm_failed"] += not valid

        md = "\n".join([f"# {d}", "", "## Evidence", ""] + rows + ["", description, ""])
        name = "dir-" + hashlib.sha256(d.encode("utf-8")).hexdigest()
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
    print(scrub(json.dumps({**stats, **checks, "output_dir": str(out)})))
    passed = (all(checks.values()) and stats["files"] > 0 and stats["llm_success"] > 0
              and not stats["usage_unknown"])
    return 0 if passed else 1


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
            return f"## LLM\n\nrequest rejected (HTTP {resp.status_code})", False
        resp.raise_for_status()
        data = resp.json()
        served = data.get("model", "?")
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            return "## LLM\n\ninvalid response", False
        sections = re.fullmatch(r"### Observed\s*\n(.*?)\n### Inferred\s*\n(.*)",
                                content.strip(), re.DOTALL)
        if (sections is None or not all(part.strip() for part in sections.groups())
                or len(re.findall(r"^### ", content, re.MULTILINE)) != 2):
            return "## LLM\n\ninvalid response", False
        # Shape validation is not a judgement of factual accuracy.
        return f"## LLM ({llm['model']} -> {served})\n\n{content}", True
    except Exception as exc:  # noqa: BLE001 - class name only, no URL or key
        return f"## LLM\n\ncall failed: {type(exc).__name__}", False


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "equipment.toml"))
