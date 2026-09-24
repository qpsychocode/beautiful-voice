"""Install, remove and load speech models; keeps the active one warm."""

from __future__ import annotations

import shutil
import threading
import urllib.parse
from pathlib import Path
from typing import Callable

from ..paths import models_dir
from .catalog import CATALOG, ModelSpec, by_id
from .download import DownloadCancelled, Downloader, fetch_from_mirror, is_installed, mirror_sample, probe_speed
from .engines import Engine, create_engine


class ModelNotReady(RuntimeError):
    pass


class ModelManager:
    def __init__(self, endpoint: Callable[[], str], device: Callable[[], str],
                 language: Callable[[], str] = lambda: "en", root: Path | None = None,
                 source: Callable[[], str] = lambda: "mirror") -> None:
        self.root = root or models_dir()
        self._endpoint = endpoint
        self._source = source
        self._device = device
        self._language = language  # used by models that cannot detect the language
        self._lock = threading.Lock()
        self._active_id = ""
        self._engine: Engine | None = None
        self._ready = threading.Event()
        self.status = "none"  # none | loading | ready | error
        self.error = ""
        self._on_status: list[Callable[[str], None]] = []
        self._load_generation = 0

    # --- catalog / disk -------------------------------------------------------

    def specs(self) -> list[ModelSpec]:
        return list(CATALOG)

    def path(self, spec: ModelSpec) -> Path:
        return self.root / spec.id

    def installed(self, spec: ModelSpec) -> bool:
        return is_installed(self.path(spec))

    def download(self, spec: ModelSpec, progress: Callable[[int, int], None], cancel: threading.Event) -> None:
        """Try the preferred source (our GitHub mirror by default), then the other one."""
        target = self.path(spec)

        def mirror() -> None:
            fetch_from_mirror(spec.id, target, progress, cancel)

        def huggingface() -> None:
            Downloader(self._endpoint()).fetch(spec.repo, spec.include, spec.exclude, target, progress, cancel)

        source = self._source()
        if source == "auto":
            source = self._faster_source(spec)
        order = [huggingface, mirror] if source == "huggingface" else [mirror, huggingface]
        try:
            order[0]()
        except DownloadCancelled:
            raise
        except Exception:
            if cancel.is_set():
                raise DownloadCancelled()
            # Partial files from one source can't be resumed from the other.
            shutil.rmtree(target, ignore_errors=True)
            order[1]()

    def _faster_source(self, spec: ModelSpec) -> str:
        """Time a few seconds of the biggest file from both sources at once and pick the quicker."""
        sample = mirror_sample(spec.id)
        if sample is None:
            return "huggingface"
        mirror_url, path = sample
        hf_url = f"{self._endpoint().rstrip('/')}/{spec.repo}/resolve/main/{urllib.parse.quote(path)}"
        speeds: dict[str, float] = {}
        probes = [threading.Thread(target=lambda k=k, u=u: speeds.__setitem__(k, probe_speed(u)), daemon=True)
                  for k, u in (("mirror", mirror_url), ("huggingface", hf_url))]
        for t in probes:
            t.start()
        for t in probes:
            t.join(10)
        return "huggingface" if speeds.get("huggingface", 0) > speeds.get("mirror", 0) else "mirror"

    def delete(self, spec: ModelSpec) -> None:
        if spec.id == self._active_id:
            self.set_active("")
        shutil.rmtree(self.path(spec), ignore_errors=True)

    def disk_size(self, spec: ModelSpec) -> int:
        target = self.path(spec)
        if not target.exists():
            return 0
        return sum(p.stat().st_size for p in target.rglob("*") if p.is_file())

    # --- loading -------------------------------------------------------------------

    def load(self, spec: ModelSpec) -> Engine:
        """Load a model synchronously (used by the benchmark and the active loader)."""
        if not self.installed(spec):
            raise ModelNotReady(f"{spec.name} is not downloaded")
        return create_engine(spec, self.path(spec), self._device(), self._language())

    def on_status(self, callback: Callable[[str], None]) -> None:
        self._on_status.append(callback)

    def _set_status(self, status: str, error: str = "") -> None:
        self.status, self.error = status, error
        for cb in self._on_status:
            cb(status)

    def active_id(self) -> str:
        return self._active_id

    def active_engine(self) -> Engine | None:
        return self._engine if self.status == "ready" else None

    def set_active(self, model_id: str) -> None:
        """Switch models; the new one loads in the background."""
        with self._lock:
            self._load_generation += 1
            generation = self._load_generation
            old, self._engine = self._engine, None
            self._ready.clear()
            self._active_id = model_id
        if old is not None:
            old.close()
        spec = by_id(model_id) if model_id else None
        if spec is None or not self.installed(spec):
            self._active_id = ""
            self._set_status("none")
            return
        self._set_status("loading")

        def run() -> None:
            try:
                engine = self.load(spec)
            except Exception as exc:
                with self._lock:
                    stale = generation != self._load_generation
                if not stale:
                    self._set_status("error", str(exc) or exc.__class__.__name__)
                    self._ready.set()
                return
            with self._lock:
                if generation != self._load_generation:
                    engine.close()  # the user picked something else meanwhile
                    return
                self._engine = engine
            self._set_status("ready")
            self._ready.set()

        threading.Thread(target=run, name="model-load", daemon=True).start()

    def reload(self) -> None:
        self.set_active(self._active_id)

    def engine(self, timeout: float = 120) -> Engine:
        """Wait for the active model (it may still be loading) and return it."""
        if not self._active_id:
            raise ModelNotReady("No model selected")
        if not self._ready.wait(timeout):
            raise ModelNotReady("The model is still loading")
        if self._engine is None:
            raise ModelNotReady(self.error or "The model failed to load")
        return self._engine

    def shutdown(self) -> None:
        with self._lock:
            engine, self._engine = self._engine, None
        if engine is not None:
            engine.close()
