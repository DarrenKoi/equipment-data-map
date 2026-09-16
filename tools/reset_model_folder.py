"""Refresh, set up or reset a model folder from the hub clone, without git in it.

    python tools/reset_model_folder.py                    # refresh MODEL_DIR below
    python tools/reset_model_folder.py ../other-dir       # refresh that folder
    python tools/reset_model_folder.py --reset            # full reset: MODEL_DIR and SLUG below
    python tools/reset_model_folder.py --reset ../dir x   # full reset, both overridden

Run from the hub after `git pull --ff-only`.

Refresh is the default because it is the move between agent sessions: it
overwrites the hub's tracked files in place and deletes nothing else, so
office/, the built CLI, its tests, equipment-map-suite/ and rollouts/ survive.
It prints the tracked files that changed and, among them, the build letters
that office/progress.md already marks done.

--reset is the first setup and the from-scratch restart: it keeps .venv, .env
and equipment.toml, replaces everything else with the hub's tracked files,
drops out/ and old office/, and starts a fresh ledger. It is the
engineer-guide.md section 1 setup snippet as one script.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
MODEL_DIR = HUB.parent / "equipment-data-map-qwen3"   # the model folder, beside the hub
SLUG = "qwen3"                                        # first line of its ledger
KEEP = {".venv", ".env", "equipment.toml"}
LETTERS = "equipment-data-parser"


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=HUB, check=True,
                         text=True, capture_output=True).stdout
    return out.splitlines()


def copy_tracked(model: Path, tracked):
    changed = []
    for rel in tracked:
        src, dst = HUB / rel, model / rel
        if not dst.is_file() or dst.read_bytes() != src.read_bytes():
            changed.append(rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return changed


def main(model: Path, slug: str):
    tracked = tracked_files()
    model.mkdir(exist_ok=True)
    for item in model.iterdir():
        if item.name in KEEP:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    copy_tracked(model, tracked)
    for name in KEEP - {".venv"}:              # secrets travel with the copy if present
        if (HUB / name).is_file() and not (model / name).exists():
            shutil.copy2(HUB / name, model / name)
    (model / "office" / "problems").mkdir(parents=True)
    (model / "office" / "progress.md").write_text(
        f"# Progress\n\nModel: {slug}. Append-only. "
        "Format is in equipment-data-parser/index.md.\n", encoding="utf-8")
    print(f"reset {model} from {HUB}: {len(tracked)} files, ledger for {slug}")


def refresh(model: Path):
    if not (model / LETTERS).is_dir():
        sys.exit(f"{model} has no {LETTERS}/: set it up with a full reset first")
    tracked = tracked_files()
    changed = copy_tracked(model, tracked)
    # The letters folder is the hub's alone (AGENTS.md), so anything untracked
    # in it is a retired letter or a contract violation. Drop it either way.
    hub_owned = set(tracked)
    stale = [p for p in (model / LETTERS).rglob("*")
             if p.is_file() and p.relative_to(model).as_posix() not in hub_owned]
    for p in stale:
        p.unlink()
    print(f"refreshed {model} from {HUB}: {len(changed)} of {len(tracked)} files changed, "
          f"{len(stale)} stale removed. office/ and build outputs untouched.")
    for rel in changed + [f"removed {p.relative_to(model)}" for p in stale]:
        print(f"  {rel}")
    touched = {m[1] for m in (re.fullmatch(rf"{LETTERS}/(\d\d)-.*\.md", r)
                              for r in changed) if m}
    ledger = model / "office" / "progress.md"
    done = set(re.findall(r"^- (\d\d) done ", ledger.read_text(encoding="utf-8"), re.M)
               ) if ledger.is_file() else set()
    redo = sorted(touched & done)
    if redo:
        print("changed letters already marked done: " + " ".join(redo))
        print("  the next session finds these itself from the `letter:` hash in its done "
              "lines and redoes them; nothing to pass on by hand.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--refresh"]   # the old spelling of the default
    if args and args[0] == "--reset":
        rest = args[1:]
        if not rest:
            main(MODEL_DIR, SLUG)
        elif len(rest) == 2:
            main(Path(rest[0]).resolve(), rest[1])
        else:
            sys.exit(__doc__)
    elif not args:
        refresh(MODEL_DIR)
    elif len(args) == 1:
        refresh(Path(args[0]).resolve())
    else:
        sys.exit(__doc__)
