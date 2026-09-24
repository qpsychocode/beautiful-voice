"""Mirror every catalog model into a GitHub release, so the app can download
models without Hugging Face.

    python tools/mirror_models.py [model-id ...]

Files are uploaded as release assets named ``<model-id>--<file>``; files over
1.9 GB (GitHub's per-asset limit is 2 GB) are split into ``.001``, ``.002``…
parts. ``manifest.json`` lists every file with its size, SHA-256 and parts.
Models already on this computer are uploaded from there; others are fetched
from Hugging Face into a staging folder, uploaded, and deleted again.
Needs the GitHub CLI (``gh``) logged in with write access to the repo.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from beautiful_voice.models.catalog import CATALOG, by_id  # noqa: E402
from beautiful_voice.models.download import (  # noqa: E402
    MIRROR_PART_SIZE as PART_SIZE, MIRROR_REPO, MIRROR_TAG, Downloader, is_installed, list_files, select_files,
)
from beautiful_voice.paths import models_dir  # noqa: E402

HF = "https://huggingface.co"


def gh(*args: str, capture: bool = False) -> str:
    result = subprocess.run(["gh", *args], check=True, text=True, capture_output=capture)
    return result.stdout if capture else ""


def ensure_release() -> None:
    try:
        gh("release", "view", MIRROR_TAG, "-R", MIRROR_REPO, capture=True)
    except subprocess.CalledProcessError:
        notes = Path(__file__).with_name("MODELS_NOTICE.md").read_text(encoding="utf-8")
        gh("release", "create", MIRROR_TAG, "-R", MIRROR_REPO, "--title", "Speech models",
           "--notes", notes, "--latest=false")


def existing_assets() -> set[str]:
    out = gh("release", "view", MIRROR_TAG, "-R", MIRROR_REPO, "--json", "assets", capture=True)
    return {a["name"] for a in json.loads(out)["assets"]}


def load_manifest() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            gh("release", "download", MIRROR_TAG, "-R", MIRROR_REPO, "-p", "manifest.json", "-D", tmp)
            return json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
        except subprocess.CalledProcessError:
            return {"version": 1, "models": {}}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def upload(paths: list[Path]) -> None:
    for p in paths:
        print(f"    uploading {p.name} ({p.stat().st_size / 1e6:.0f} MB)", flush=True)
        gh("release", "upload", MIRROR_TAG, str(p), "-R", MIRROR_REPO, "--clobber")


def mirror(model_id: str, manifest: dict, assets: set[str]) -> None:
    spec = by_id(model_id)
    files = select_files(list_files(HF, spec.repo), spec.include, spec.exclude)
    local = models_dir() / spec.id
    staging = None
    if not is_installed(local):
        staging = Path(tempfile.mkdtemp(prefix=f"bv-{spec.id}-"))
        print(f"  fetching {spec.id} from Hugging Face", flush=True)
        Downloader(HF).fetch(spec.repo, spec.include, spec.exclude, staging, lambda d, t: None, threading.Event())
        local = staging
    entries = []
    try:
        for f in files:
            src = local / f.path
            base = f"{spec.id}--{f.path.replace('/', '--')}"
            digest = sha256(src)
            if src.stat().st_size <= PART_SIZE:
                parts = [base]
                if base not in assets:
                    # The asset takes its name from the file, so upload a link with the right name.
                    named = Path(tempfile.gettempdir()) / base
                    named.unlink(missing_ok=True)
                    try:
                        os.link(src, named)
                    except OSError:
                        shutil.copyfile(src, named)
                    upload([named])
                    named.unlink()
            else:
                parts = []
                with open(src, "rb") as fh:
                    index = 1
                    while True:
                        chunk = fh.read(PART_SIZE)
                        if not chunk:
                            break
                        name = f"{base}.{index:03d}"
                        parts.append(name)
                        if name not in assets:
                            part_path = Path(tempfile.gettempdir()) / name
                            part_path.write_bytes(chunk)
                            upload([part_path])
                            part_path.unlink()
                        index += 1
            entries.append({"path": f.path, "size": src.stat().st_size, "sha256": digest, "parts": parts})
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
    manifest["models"][spec.id] = {"source": spec.repo, "files": entries}


def main() -> None:
    ids = sys.argv[1:] or [s.id for s in CATALOG]
    ensure_release()
    manifest = load_manifest()
    for model_id in ids:
        assets = existing_assets()
        print(f"== {model_id}", flush=True)
        mirror(model_id, manifest, assets)
        out = Path(tempfile.gettempdir()) / "manifest.json"
        out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        upload([out])  # after every model, so a partial run is still usable
    print("done", flush=True)


if __name__ == "__main__":
    main()
