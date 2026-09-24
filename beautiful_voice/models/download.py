"""Resumable model downloads from Hugging Face with byte-level progress.

Only the files a model needs are fetched (glob patterns from the catalog).
Each file lands as ``*.part`` first and is renamed when complete, and a
``.installed.json`` marker is written last, so an interrupted download never
looks installed.
"""

from __future__ import annotations

import fnmatch
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


class DownloadCancelled(Exception):
    pass


@dataclass
class RemoteFile:
    path: str
    size: int


def _get_json(url: str, timeout: float = 30) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_files(endpoint: str, repo: str, revision: str = "main") -> list[RemoteFile]:
    url = f"{endpoint.rstrip('/')}/api/models/{repo}/tree/{revision}?recursive=true"
    items = _get_json(url)
    files = []
    for item in items:  # type: ignore[union-attr]
        if item.get("type") != "file":
            continue
        size = item.get("lfs", {}).get("size") or item.get("size") or 0
        files.append(RemoteFile(item["path"], int(size)))
    return files


def select_files(files: list[RemoteFile], include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> list[RemoteFile]:
    chosen = []
    for f in files:
        name = f.path
        if any(fnmatch.fnmatch(name, p) for p in include) and not any(fnmatch.fnmatch(name, p) for p in exclude):
            chosen.append(f)
    return chosen


def is_installed(target: Path) -> bool:
    return (target / MARKER).exists()


class Downloader:
    def __init__(self, endpoint: str = "https://huggingface.co") -> None:
        self.endpoint = (endpoint or "https://huggingface.co").rstrip("/")

    def fetch(
        self,
        repo: str,
        include: tuple[str, ...],
        exclude: tuple[str, ...],
        target: Path,
        progress: Callable[[int, int], None],
        cancel: threading.Event,
        revision: str = "main",
    ) -> None:
        files = select_files(list_files(self.endpoint, repo, revision), include, exclude)
        if not files:
            raise RuntimeError(f"No matching files found in {repo}")
        target.mkdir(parents=True, exist_ok=True)
        total = sum(f.size for f in files)
        done = 0
        last_report = 0.0
        for f in files:
            dest = target / f.path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() and (not f.size or dest.stat().st_size == f.size):
                done += f.size
                continue
            part = dest.with_name(dest.name + ".part")
            have = part.stat().st_size if part.exists() else 0
            if f.size and have > f.size:
                part.unlink()
                have = 0
            url = f"{self.endpoint}/{repo}/resolve/{revision}/{urllib.parse.quote(f.path)}"
            headers = {"User-Agent": USER_AGENT}
            if have:
                headers["Range"] = f"bytes={have}-"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                if have and resp.status != 206:
                    have = 0  # server ignored the range; start over
                mode = "ab" if have else "wb"
                done += have
                with open(part, mode) as out:
                    while True:
                        if cancel.is_set():
                            raise DownloadCancelled()
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        out.write(chunk)
                        done += len(chunk)
                        now = time.monotonic()
                        if now - last_report > 0.15:
                            progress(done, total)
                            last_report = now
            if f.size and part.stat().st_size != f.size:
                raise RuntimeError(f"Incomplete download: {f.path}")
            os.replace(part, dest)
        progress(total, total)
        (target / MARKER).write_text(
            json.dumps({"repo": repo, "revision": revision, "files": [f.path for f in files], "bytes": total,
                        "installed": time.time()}),
            encoding="utf-8",
        )
