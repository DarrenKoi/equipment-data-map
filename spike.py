"""ftp -> LLM -> markdown spike for one equipment. ``python spike.py equipment.toml``.

Walks the configured roots read-only, samples the newest file per extension in
each directory, asks the office LLM once per directory, and writes one markdown
per directory plus ``index.md``. Ends with a three-condition self-check.
Letter: equipment-data-parser/00-spike.md.
"""

import fnmatch
import hashlib
import json
import math
import os
import posixpath
import re
import sys
import tempfile
import tomllib
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import requests

from ftp_handler import fleet_downloader
from ftp_handler.direct_downloader import HostSpec, ListDir
from ftp_handler.direct_downloader.fleet_downloader import SizingReport

# Site-wide noise, always excluded on top of `deny`, matched case-insensitively
# on each path segment below its root (so a Temp/ directory is skipped whole).
# The configured root itself is the engineer's choice and is never noise. Add to these lists as more FAB tools are surveyed.
NOISE_EXTENSIONS = ["bak", "iso", "lock"]
# A word counts only when no letter touches it: temp.txt and log_tmp_1.csv are
# noise, temperature.log and template.xml are kept.
NOISE_WORDS = ["temp", "tmp"]
NOISE = re.compile(
    r"\.(?:%s)$|(?<![a-z])(?:%s)(?![a-z])"
    % ("|".join(map(re.escape, NOISE_EXTENSIONS)), "|".join(map(re.escape, NOISE_WORDS))),
    re.IGNORECASE)

PROMPT = (
    "You record facts about one directory of a FAB equipment file store. "
    "Reply in markdown with exactly one section, '### Observed', listing only what "
    "the listing and samples show: file names and naming patterns, extensions, "
    "sizes, modification times, formats, and field names or values visible in the "
    "samples. One directory cannot reveal the tool's purpose, so state no purpose "
    "or guess; those come later from facts across directories. Be brief."
)


def load_config(config_path, *, require_credentials=True):
    try:
        cfg = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        if require_credentials:
            raise
        cfg = {}
    defaults = {
        "equipment": {"host": "", "user": "", "password": "",
                      "name": "tool", "port": 21, "roots": ["/"], "deny": []},
        "budget": {"max_download_bytes": 0, "max_dirs": 20, "sample_bytes": 8192},
        "llm": {"url": "", "model": "", "api_key": "", "timeout_s": 60},
        "output": {"dir": "out"},
    }
    for section, fields in defaults.items():
        values = cfg.setdefault(section, {})
        if not isinstance(values, dict):
            raise ValueError("Expected a configuration table")
        for key, value in fields.items():
            if key not in values or (isinstance(values[key], str) and not values[key].strip()):
                values[key] = value
    eq, budget, llm = cfg["equipment"], cfg["budget"], cfg["llm"]
    if any(not isinstance(eq[key], str) or (require_credentials and not eq[key].strip())
           for key in ("host", "user", "password")):
        raise ValueError("FTP host, user and password are required for connection")
    # Empty lists and zero budgets are intentional restrictions, not missing values.
    if not isinstance(eq["name"], str) or eq["name"] in (".", "..") or any(c in eq["name"] for c in '/\\:'):
        raise ValueError("Equipment name must be one directory component")
    if type(eq["port"]) is not int or not 1 <= eq["port"] <= 65535:
        raise ValueError("Invalid FTP port")
    for key in ("roots", "deny"):
        if not isinstance(eq[key], list) or any(not isinstance(v, str) or not v for v in eq[key]):
            raise ValueError("Paths and patterns must be string lists")
    if any(not p.startswith("/") for p in eq["roots"]):
        raise ValueError("FTP roots must be absolute")
    if any(type(budget[key]) is not int or budget[key] < 0
           for key in ("max_dirs", "max_download_bytes", "sample_bytes")):
        raise ValueError("Budgets must be nonnegative integers")
    if any(not isinstance(llm[key], str) for key in ("url", "model", "api_key")):
        raise ValueError("LLM settings must be strings")
    if type(llm["timeout_s"]) not in (int, float) or not math.isfinite(llm["timeout_s"]) or llm["timeout_s"] <= 0:
        raise ValueError("LLM timeout must be finite and positive")
    if not isinstance(cfg["output"]["dir"], str):
        raise ValueError("Output directory must be a string")
    if bool(llm["url"]) != bool(llm["model"]):
        raise ValueError("Configure both LLM URL and model, or neither")
    return cfg


def prepare_config(config_path):
    """Create or fill local configuration; leave unknown credentials blank."""
    path = Path(config_path)
    temporary = None
    try:
        cfg = load_config(path, require_credentials=False)
        # The spike config consists of flat TOML tables. Round-trip before replacing
        # anything, so unsupported custom values leave the original file untouched.
        body = "\n".join(
            f'[{json.dumps(section)}]\n' + "".join(
                f'{json.dumps(key)} = {json.dumps(value, ensure_ascii=False, allow_nan=False)}\n'
                for key, value in values.items())
            for section, values in cfg.items())
        if tomllib.loads(body) != cfg:
            raise ValueError("Configuration round-trip failed")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".equipment-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError, AttributeError):
        print('{"config_ready": false, "error": "Check TOML syntax, required FTP fields and optional field types locally"}')
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    missing = [f"equipment.{key}" for key in ("host", "user", "password")
               if not cfg["equipment"][key].strip()]
    print(json.dumps({"config_ready": False, "missing_fields": missing} if missing
                     else {"config_ready": True}))
    return 0


def main(config_path):
    try:
        cfg = load_config(config_path)
    except (OSError, ValueError, TypeError):
        print('{"config_ready": false, "error": "Check TOML syntax, FTP host/user/password and optional settings; LLM URL and model must be paired"}')
        return 1
    eq, budget, llm = cfg["equipment"], cfg["budget"], cfg["llm"]
    llm_enabled = bool(llm["url"] and llm["model"])
    secrets = [s for s in (eq.get("password"), llm.get("api_key")) if s]

    def scrub(text):  # rule: secrets never reach stdout or any output file
        for s in secrets:
            text = text.replace(s, "***")
        return text

    roots = list(dict.fromkeys(posixpath.normpath(r) for r in eq["roots"]))

    def inside(path):
        p = posixpath.normpath(path)
        return any(p == r or p.startswith(r.rstrip("/") + "/") for r in roots)

    def denied(path):  # patterns match absolute paths, root-relative paths, or basenames
        below = [posixpath.relpath(path, root).split("/") for root in roots
                 if path.startswith(root.rstrip("/") + "/")]
        candidates = {path, posixpath.basename(path)}
        for root in roots:
            if path != root and not path.startswith(root.rstrip("/") + "/"):
                continue
            relative = posixpath.relpath(path, root)
            while relative not in ("", "."):
                candidates.update((relative, posixpath.basename(relative),
                                   posixpath.normpath(posixpath.join(root, relative))))
                relative = posixpath.dirname(relative)
        return any(NOISE.search(part) for parts in below for part in parts) or any(
            fnmatch.fnmatch(candidate, pattern)
            for pattern in eq.get("deny", []) for candidate in candidates)

    def allowed(path):
        return inside(path) and not denied(posixpath.normpath(path))

    dl = fleet_downloader()(
        user=eq["user"], password=eq["password"], port=eq.get("port", 21),
        max_concurrency=1, passive=True,
    )
    spec = lambda **kw: HostSpec(eq["host"], **kw)  # one host, the fleet of one

    out = Path(cfg.get("output", {}).get("dir", "out")) / eq["name"] / uuid4().hex
    out.mkdir(parents=True, exist_ok=False)
    stats = {"mode": "llm" if llm_enabled else "metadata-only" if budget["max_download_bytes"] == 0 else "samples-only",
             "dirs": 0, "files": 0, "bytes": 0, "estimated_bytes": 0,
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
        if files and not llm_enabled:
            description = "## LLM\n\nnot configured; interpretation not performed"
        elif files:
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
    passed = (all(checks.values()) and stats["files"] > 0 and (not llm_enabled or stats["llm_success"] > 0)
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
        observed = re.fullmatch(r"### Observed\s*\n(.*)", content.strip(), re.DOTALL)
        if (observed is None or not observed.group(1).strip()
                or len(re.findall(r"^### ", content, re.MULTILINE)) != 1):
            return "## LLM\n\ninvalid response", False
        # Shape validation is not a judgement of factual accuracy.
        return f"## LLM ({llm['model']} -> {served})\n\n{content}", True
    except Exception as exc:  # noqa: BLE001 - class name only, no URL or key
        return f"## LLM\n\ncall failed: {type(exc).__name__}", False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--prepare-config":
        sys.exit(prepare_config(sys.argv[2] if len(sys.argv) > 2 else "equipment.toml"))
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "equipment.toml"))
