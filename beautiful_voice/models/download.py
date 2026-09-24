"""Resumable model downloads with byte-level progress.

Models come from our own mirror (assets of a GitHub release, listed in
``manifest.json``) so the app works without Hugging Face; Hugging Face is the
fallback. Each file lands as ``*.part`` first and is renamed when complete,
and a ``.installed.json`` marker is written last, so an interrupted download
never looks installed and resumes where it stopped.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

MARKER = ".installed.json"
USER_AGENT = "BeautifulVoice/0.1 (+https://github.com/qpsychocode/beautiful-voice)"
CHUNK = 1024 * 256

MIRROR_REPO = "qpsychocode/beautiful-voice"
MIRROR_TAG = "models-v1"
MIRROR_BASE = f"https://github.com/{MIRROR_REPO}/releases/download/{MIRROR_TAG}"
MIRROR_PART_SIZE = 1_900_000_000  # GitHub allows 2 GB per release asset

Progress = Callable[[int, int], None]


class DownloadCancelled(Exception):
    pass


class MirrorUnavailable(Exception):
    """The mirror can't serve this model (not uploaded yet, or unreachable)."""


@dataclass
class RemoteFile:
    path: str
    size: int


def _get_json(url: str, timeout: float = 30) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_installed(target: Path) -> bool:
    return (target / MARKER).exists()


def _write_marker(target: Path, source: str, files: list[str], total: int) -> None:
    (target / MARKER).write_text(
        json.dumps({"source": source, "files": files, "bytes": total, "installed": time.time()}),
        encoding="utf-8",
    )


class _Transfer:
    """Shared byte counter so progress covers the whole model, not one file."""

    def __init__(self, total: int, progress: Progress, cancel: threading.Event) -> None:
        self.total, self.done = total, 0
        self.progress, self.cancel = progress, cancel
        self._last = 0.0

    def add(self, n: int) -> None:
        self.done += n
        now = time.monotonic()
        if now - self._last > 0.15:
            self.progress(self.done, self.total)
            self._last = now

    def stream(self, url: str, out: Path, start: int) -> None:
        """Append ``url`` (from byte ``start``) to ``out``."""
        headers = {"User-Agent": USER_AGENT}
        if start:
            headers["Range"] = f"bytes={start}-"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            if start and resp.status != 206:
                raise IOError("server ignored the resume request")
            with open(out, "ab") as fh:
                while True:
                    if self.cancel.is_set():
                        raise DownloadCancelled()
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    fh.write(chunk)
                    self.add(len(chunk))


# --- our mirror ---------------------------------------------------------------

_manifest: dict | None = None


def mirror_manifest() -> dict:
    global _manifest
    if _manifest is None:
        try:
            _manifest = _get_json(f"{MIRROR_BASE}/manifest.json", timeout=20)  # type: ignore[assignment]
        except Exception as exc:
            raise MirrorUnavailable(str(exc)) from exc
    return _manifest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_from_mirror(model_id: str, target: Path, progress: Progress, cancel: threading.Event) -> None:
    entry = mirror_manifest().get("models", {}).get(model_id)
    if not entry:
        raise MirrorUnavailable(f"{model_id} is not on the mirror")
    files = entry["files"]
    target.mkdir(parents=True, exist_ok=True)
    transfer = _Transfer(sum(f["size"] for f in files), progress, cancel)
    for f in files:
        dest = target / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size == f["size"]:
            transfer.add(f["size"])
            continue
        part = dest.with_name(dest.name + ".part")
        have = part.stat().st_size if part.exists() else 0
        if have > f["size"]:
            part.unlink()
            have = 0
        transfer.add(have)
        offset = 0
        for asset in f["parts"]:
            length = min(MIRROR_PART_SIZE, f["size"] - offset)
            if have < offset + length:  # this piece is not fully on disk yet
                url = f"{MIRROR_BASE}/{urllib.parse.quote(asset)}"
                try:
                    transfer.stream(url, part, have - offset)
                except IOError:
                    # Can't resume inside this piece: drop it and fetch it whole.
                    with open(part, "r+b") as fh:
                        fh.truncate(offset)
                    transfer.done -= have - offset
                    transfer.stream(url, part, 0)
                have = offset + length
            offset += length
        if part.stat().st_size != f["size"] or _sha256(part) != f["sha256"]:
            part.unlink()
            raise IOError(f"{f['path']} arrived damaged; try again")
        os.replace(part, dest)
    progress(transfer.total, transfer.total)
    _write_marker(target, f"mirror:{MIRROR_TAG}", [f["path"] for f in files], transfer.total)


def probe_speed(url: str, seconds: float = 4.0, limit: int = 8 << 20) -> float:
    """Bytes per second for the start of ``url``; 0 if it can't be reached."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": f"bytes=0-{limit - 1}"})
    started = time.monotonic()
    got = 0
    try:
        with urllib.request.urlopen(req, timeout=seconds + 2) as resp:
            while got < limit and time.monotonic() - started < seconds:
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                got += len(chunk)
    except Exception:
        return 0.0
    return got / max(time.monotonic() - started, 1e-3)


def mirror_sample(model_id: str) -> tuple[str, str] | None:
    """(mirror URL, file path) of the model's largest file, for a speed probe."""
    try:
        entry = mirror_manifest().get("models", {}).get(model_id)
    except MirrorUnavailable:
        return None
    if not entry:
        return None
    biggest = max(entry["files"], key=lambda f: f["size"])
    return f"{MIRROR_BASE}/{urllib.parse.quote(biggest['parts'][0])}", biggest["path"]


# --- Hugging Face ------------------------------------------------------------------

def list_files(endpoint: str, repo: str, revision: str = "main") -> list[RemoteFile]:
    url = f"{endpoint.rstrip('/')}/api/models/{repo}/tree/{revision}?recursive=true"
    files = []
    for item in _get_json(url):  # type: ignore[union-attr]
        if item.get("type") != "file":
            continue
        size = item.get("lfs", {}).get("size") or item.get("size") or 0
        files.append(RemoteFile(item["path"], int(size)))
    return files


def select_files(files: list[RemoteFile], include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> list[RemoteFile]:
    return [f for f in files
            if any(fnmatch.fnmatch(f.path, p) for p in include) and not any(fnmatch.fnmatch(f.path, p) for p in exclude)]


class Downloader:
    """Downloads straight from a Hugging Face repository (or a mirror of it)."""

    def __init__(self, endpoint: str = "https://huggingface.co") -> None:
        self.endpoint = (endpoint or "https://huggingface.co").rstrip("/")

    def fetch(self, repo: str, include: tuple[str, ...], exclude: tuple[str, ...], target: Path,
              progress: Progress, cancel: threading.Event, revision: str = "main") -> None:
        files = select_files(list_files(self.endpoint, repo, revision), include, exclude)
        if not files:
            raise RuntimeError(f"No matching files found in {repo}")
        target.mkdir(parents=True, exist_ok=True)
        transfer = _Transfer(sum(f.size for f in files), progress, cancel)
        for f in files:
            dest = target / f.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and (not f.size or dest.stat().st_size == f.size):
                transfer.add(f.size)
                continue
            part = dest.with_name(dest.name + ".part")
            have = part.stat().st_size if part.exists() else 0
            if f.size and have > f.size:
                part.unlink()
                have = 0
            transfer.add(have)
            url = f"{self.endpoint}/{repo}/resolve/{revision}/{urllib.parse.quote(f.path)}"
            try:
                transfer.stream(url, part, have)
            except IOError:
                part.unlink(missing_ok=True)
                transfer.done -= have
                transfer.stream(url, part, 0)
            if f.size and part.stat().st_size != f.size:
                raise RuntimeError(f"Incomplete download: {f.path}")
            os.replace(part, dest)
        progress(transfer.total, transfer.total)
        _write_marker(target, f"huggingface:{repo}", [f.path for f in files], transfer.total)
