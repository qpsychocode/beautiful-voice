"""Where Beautiful Voice keeps its files.

Settings and history live in the roaming profile, downloaded models in the
local (non-roaming) one because they are large. ``BEAUTIFUL_VOICE_HOME``
overrides both, which is handy for portable installs and tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "BeautifulVoice"
APP_TITLE = "Beautiful Voice"
APP_VERSION = "0.1.0"
REPO_URL = "https://github.com/qpsycho/beautiful-voice"


def _home_override() -> Path | None:
    value = os.environ.get("BEAUTIFUL_VOICE_HOME")
    return Path(value) if value else None


def data_dir() -> Path:
    override = _home_override()
    if override:
        path = override
    elif sys.platform == "win32":
        path = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    override = _home_override()
    if os.environ.get("BEAUTIFUL_VOICE_MODELS"):
        path = Path(os.environ["BEAUTIFUL_VOICE_MODELS"])
    elif override:
        path = override / "models"
    elif sys.platform == "win32":
        path = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME / "models"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME / "models"
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def qml_dir() -> Path:
    return package_dir() / "qml"


def assets_dir() -> Path:
    return package_dir() / "assets"
