"""Set up or reset a model folder from the hub clone, without git in the model folder.

    python tools/reset_model_folder.py                 # uses MODEL_DIR and SLUG below
    python tools/reset_model_folder.py ../other-dir x  # or override both

Run from the hub after `git pull --ff-only`. Keeps .venv, .env and
equipment.toml in the model folder; replaces everything else with the hub's
tracked files, drops out/ and old office/, and starts a fresh ledger.
This is the engineer-guide.md section 1 setup snippet as one script.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
MODEL_DIR = HUB.parent / "equipment-data-map-qwen3"   # the model folder, beside the hub
SLUG = "qwen3"                                        # first line of its ledger
KEEP = {".venv", ".env", "equipment.toml"}


def main(model: Path, slug: str):
    tracked = subprocess.run(["git", "ls-files"], cwd=HUB, check=True,
                             text=True, capture_output=True).stdout.split()
    model.mkdir(exist_ok=True)
    for item in model.iterdir():
        if item.name in KEEP:
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    for rel in tracked:
        dst = model / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HUB / rel, dst)
    for name in KEEP - {".venv"}:              # secrets travel with the copy if present
        if (HUB / name).is_file() and not (model / name).exists():
            shutil.copy2(HUB / name, model / name)
    (model / "office" / "problems").mkdir(parents=True)
    (model / "office" / "progress.md").write_text(
        f"# Progress\n\nModel: {slug}. Append-only. "
        "Format is in equipment-data-parser/index.md.\n", encoding="utf-8")
    print(f"reset {model} from {HUB}: {len(tracked)} files, ledger for {slug}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        main(MODEL_DIR, SLUG)
    elif len(sys.argv) == 3:
        main(Path(sys.argv[1]).resolve(), sys.argv[2])
    else:
        sys.exit(__doc__)
