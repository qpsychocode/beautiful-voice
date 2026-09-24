"""Start with the system: the per-user Run key on Windows, a LaunchAgent on macOS."""

from __future__ import annotations

import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "BeautifulVoice"
AGENT_LABEL = "com.qpsycho.beautifulvoice"


def supported() -> bool:
    return sys.platform in ("win32", "darwin")


def _launch_args() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--minimized"]
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    launcher = Path(__file__).resolve().parent.parent / "run.pyw"
    return [str(pythonw if pythonw.exists() else exe), str(launcher), "--minimized"]


def command() -> str:
    return " ".join(f'"{a}"' if a != "--minimized" else a for a in _launch_args())


def _agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{AGENT_LABEL}.plist"


def set_enabled(enabled: bool) -> None:
    if sys.platform == "win32":
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, VALUE, 0, winreg.REG_SZ, command())
            else:
                try:
                    winreg.DeleteValue(key, VALUE)
                except FileNotFoundError:
                    pass
    elif sys.platform == "darwin":
        import plistlib

        path = _agent_path()
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as fh:
                plistlib.dump({"Label": AGENT_LABEL, "ProgramArguments": _launch_args(), "RunAtLoad": True}, fh)
        else:
            path.unlink(missing_ok=True)


def is_enabled() -> bool:
    if sys.platform == "darwin":
        return _agent_path().exists()
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE)
            return True
    except FileNotFoundError:
        return False
