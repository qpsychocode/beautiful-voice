"""System-wide hotkey.

On Windows the combo is registered with ``RegisterHotKey``: the OS swallows
it, so the focused app never sees the keystroke. Hold-to-talk polls the key
state after the press to catch the release. Other platforms fall back to
pynput, which observes keys without swallowing them.
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable

MODIFIERS = ("ctrl", "alt", "shift", "win")

# Virtual-key codes for the non-alphanumeric keys we accept.
_NAMED_VK = {
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "backspace": 0x08, "esc": 0x1B,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "pause": 0x13, "capslock": 0x14, "scrolllock": 0x91, "printscreen": 0x2C,
    "`": 0xC0, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD, "\\": 0xDC,
    ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF,
}
for _i in range(1, 25):
    _NAMED_VK[f"f{_i}"] = 0x6F + _i
for _c in "abcdefghijklmnopqrstuvwxyz":
    _NAMED_VK[_c] = ord(_c.upper())
for _d in "0123456789":
    _NAMED_VK[_d] = ord(_d)

_MOD_BITS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
_MOD_VKS = {"alt": (0x12,), "ctrl": (0x11,), "shift": (0x10,), "win": (0x5B, 0x5C)}
MOD_NOREPEAT = 0x4000


@dataclass(frozen=True)
class Combo:
    modifiers: tuple[str, ...]
    key: str

    @property
    def vk(self) -> int:
        return _NAMED_VK[self.key]

    def __str__(self) -> str:
        return "+".join([*self.modifiers, self.key])


def parse_combo(text: str) -> Combo:
    parts = [p.strip().lower() for p in text.replace(" ", "").split("+") if p.strip()]
    aliases = {"control": "ctrl", "option": "alt", "cmd": "win", "meta": "win", "super": "win",
               "escape": "esc", "return": "enter", "del": "delete", "pgup": "pageup", "pgdn": "pagedown"}
    parts = [aliases.get(p, p) for p in parts]
    mods = tuple(m for m in MODIFIERS if m in parts)
    keys = [p for p in parts if p not in MODIFIERS]
    if len(keys) != 1:
        raise ValueError(f"A hotkey needs exactly one non-modifier key: {text!r}")
    if keys[0] not in _NAMED_VK:
        raise ValueError(f"Unsupported key: {keys[0]!r}")
    if not mods and not keys[0].startswith("f"):
        raise ValueError("Use at least one modifier (Ctrl, Alt, Shift or Win) with this key")
    return Combo(mods, keys[0])


class HotkeyService:
    """Calls ``on_press`` / ``on_release`` from a background thread."""

    def __init__(self, on_press: Callable[[], None], on_release: Callable[[], None],
                 on_escape: Callable[[], None]) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self.on_escape = on_escape
        self.hold_mode = False
        if sys.platform == "win32":
            self._impl: _WindowsHotkeys | _PynputHotkeys = _WindowsHotkeys(self)
        else:
            self._impl = _PynputHotkeys(self)

    def start(self, combo: str) -> str | None:
        """Start listening. Returns an error message, or None on success."""
        return self._impl.start(parse_combo(combo))

    def rebind(self, combo: str) -> str | None:
        try:
            parsed = parse_combo(combo)
        except ValueError as exc:
            return str(exc)
        return self._impl.rebind(parsed)

    def grab_escape(self, enabled: bool) -> None:
        """While recording, Esc cancels. Outside of that it stays with the apps."""
        self._impl.grab_escape(enabled)

    def stop(self) -> None:
        self._impl.stop()


class _WindowsHotkeys:
    WM_HOTKEY = 0x0312
    WM_APP = 0x8000
    MSG_REBIND = WM_APP + 1
    MSG_ESC_ON = WM_APP + 2
    MSG_ESC_OFF = WM_APP + 3
    MSG_QUIT = 0x0012
    ID_MAIN = 1
    ID_ESC = 2

    def __init__(self, owner: HotkeyService) -> None:
        import ctypes
        from ctypes import wintypes

        self.ct = ctypes
        self.wt = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.owner = owner
        self.combo: Combo | None = None
        self._pending: Combo | None = None
        self._thread: threading.Thread | None = None
        self._thread_id = 0
        self._ready = threading.Event()
        self._result: str | None = None
        self._result_ready = threading.Event()
        self._holding = False

    def _register(self, combo: Combo) -> str | None:
        mods = sum(_MOD_BITS[m] for m in combo.modifiers) | MOD_NOREPEAT
        if not self.user32.RegisterHotKey(None, self.ID_MAIN, mods, combo.vk):
            return "busy"
        return None

    def _key_down(self, vk: int) -> bool:
        return bool(self.user32.GetAsyncKeyState(vk) & 0x8000)

    def _combo_held(self, combo: Combo) -> bool:
        if not self._key_down(combo.vk):
            return False
        return all(any(self._key_down(v) for v in _MOD_VKS[m]) for m in combo.modifiers)

    def _watch_release(self, combo: Combo) -> None:
        # Runs on its own thread so the message loop keeps serving Esc.
        time.sleep(0.03)
        while self._combo_held(combo):
            time.sleep(0.015)
        self._holding = False
        self.owner.on_release()

    def _loop(self, combo: Combo) -> None:
        self._thread_id = self.kernel32.GetCurrentThreadId()
        msg = self.wt.MSG()
        # Make sure the thread has a message queue before anyone posts to it.
        self.user32.PeekMessageW(self.ct.byref(msg), None, 0, 0, 0)
        self._result = self._register(combo)
        if self._result is None:
            self.combo = combo
        self._ready.set()
        while self.user32.GetMessageW(self.ct.byref(msg), None, 0, 0) > 0:
            if msg.message == self.WM_HOTKEY:
                if msg.wParam == self.ID_ESC:
                    self.owner.on_escape()
                elif msg.wParam == self.ID_MAIN and self.combo is not None:
                    if self.owner.hold_mode:
                        if self._holding:
                            continue
                        self._holding = True
                        self.owner.on_press()
                        threading.Thread(target=self._watch_release, args=(self.combo,), daemon=True).start()
                    else:
                        self.owner.on_press()
            elif msg.message == self.MSG_REBIND and self._pending is not None:
                new, self._pending = self._pending, None
                self.user32.UnregisterHotKey(None, self.ID_MAIN)
                error = self._register(new)
                if error is None:
                    self.combo = new
                elif self.combo is not None:
                    self._register(self.combo)  # put the old one back
                self._result = error
                self._result_ready.set()
            elif msg.message == self.MSG_ESC_ON:
                self.user32.RegisterHotKey(None, self.ID_ESC, MOD_NOREPEAT, 0x1B)
            elif msg.message == self.MSG_ESC_OFF:
                self.user32.UnregisterHotKey(None, self.ID_ESC)
        self.user32.UnregisterHotKey(None, self.ID_MAIN)
        self.user32.UnregisterHotKey(None, self.ID_ESC)

    def start(self, combo: Combo) -> str | None:
        self._thread = threading.Thread(target=self._loop, args=(combo,), name="hotkeys", daemon=True)
        self._thread.start()
        self._ready.wait(3)
        return self._result

    def rebind(self, combo: Combo) -> str | None:
        if not self._thread_id:
            return self.start(combo)
        self._pending = combo
        self._result_ready.clear()
        self.user32.PostThreadMessageW(self._thread_id, self.MSG_REBIND, 0, 0)
        self._result_ready.wait(3)
        return self._result

    def grab_escape(self, enabled: bool) -> None:
        if self._thread_id:
            self.user32.PostThreadMessageW(self._thread_id, self.MSG_ESC_ON if enabled else self.MSG_ESC_OFF, 0, 0)

    def stop(self) -> None:
        if self._thread_id:
            self.user32.PostThreadMessageW(self._thread_id, self.MSG_QUIT, 0, 0)


class _PynputHotkeys:
    def __init__(self, owner: HotkeyService) -> None:
        self.owner = owner
        self.combo: Combo | None = None
        self._listener = None
        self._pressed: set[str] = set()
        self._active = False
        self._esc = False

    @staticmethod
    def _name(key) -> str:
        from pynput import keyboard

        mods = {
            keyboard.Key.ctrl: "ctrl", keyboard.Key.ctrl_l: "ctrl", keyboard.Key.ctrl_r: "ctrl",
            keyboard.Key.alt: "alt", keyboard.Key.alt_l: "alt", keyboard.Key.alt_r: "alt",
            keyboard.Key.shift: "shift", keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
            keyboard.Key.cmd: "win", keyboard.Key.cmd_l: "win", keyboard.Key.cmd_r: "win",
        }
        if key in mods:
            return mods[key]
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return getattr(key, "name", "") or ""

    def _on_press(self, key) -> None:
        name = self._name(key)
        self._pressed.add(name)
        if name == "esc" and self._esc:
            self.owner.on_escape()
            return
        combo = self.combo
        if combo and not self._active and combo.key in self._pressed and all(m in self._pressed for m in combo.modifiers):
            self._active = True
            self.owner.on_press()

    def _on_release(self, key) -> None:
        name = self._name(key)
        self._pressed.discard(name)
        combo = self.combo
        if self._active and combo and (name == combo.key or name in combo.modifiers):
            self._active = False
            if self.owner.hold_mode:
                self.owner.on_release()

    def start(self, combo: Combo) -> str | None:
        try:
            from pynput import keyboard
        except ImportError:
            return "pynput is not installed"
        self.combo = combo
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()
        return None

    def rebind(self, combo: Combo) -> str | None:
        self.combo = combo
        return None

    def grab_escape(self, enabled: bool) -> None:
        self._esc = enabled

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
