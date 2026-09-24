"""Put recognized text into whatever field has focus in another app.

"paste" puts the text on the clipboard, presses Ctrl+V and then restores what
the clipboard held before. "type" sends the characters as Unicode keystrokes,
which never touches the clipboard but is slower for long texts.
"""

from __future__ import annotations

import sys
import time

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = wintypes.HANDLE
    user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    user32.SetClipboardData.restype = wintypes.HANDLE
    user32.EnumClipboardFormats.argtypes = [wintypes.UINT]
    user32.EnumClipboardFormats.restype = wintypes.UINT
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalSize.restype = ctypes.c_size_t
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    # Formats whose handle is not a plain memory block; Windows re-creates the
    # common ones (e.g. CF_BITMAP from CF_DIB) when the block formats are restored.
    _NON_HGLOBAL = {2, 3, 9, 14, 0x80, 0x82, 0x83, 0x8E}
    _SNAPSHOT_LIMIT = 64 * 1024 * 1024

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_CONTROL, VK_V, VK_RETURN = 0x11, 0x56, 0x0D
    _HELD_MODIFIERS = (0x10, 0x11, 0x12, 0x5B, 0x5C)

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]


def foreground_window() -> int:
    if sys.platform != "win32":
        return 0
    return int(user32.GetForegroundWindow() or 0)


def window_process_id(hwnd: int) -> int:
    if sys.platform != "win32" or not hwnd:
        return 0
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


# --- Windows clipboard ------------------------------------------------------

def _open_clipboard(retries: int = 20) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(0.01)  # another app holds it for a moment
    return False


def _snapshot_clipboard() -> list[tuple[int, bytes]]:
    items: list[tuple[int, bytes]] = []
    if not _open_clipboard():
        return items
    try:
        total = 0
        fmt = user32.EnumClipboardFormats(0)
        while fmt:
            if fmt not in _NON_HGLOBAL:
                handle = user32.GetClipboardData(fmt)
                if handle:
                    size = kernel32.GlobalSize(handle)
                    ptr = kernel32.GlobalLock(handle)
                    if ptr and size and total + size <= _SNAPSHOT_LIMIT:
                        items.append((fmt, ctypes.string_at(ptr, size)))
                        total += size
                    if ptr:
                        kernel32.GlobalUnlock(handle)
            fmt = user32.EnumClipboardFormats(fmt)
    finally:
        user32.CloseClipboard()
    return items


def _put_block(fmt: int, data: bytes) -> None:
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, max(1, len(data)))
    if not handle:
        return
    ptr = kernel32.GlobalLock(handle)
    if data:
        ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(handle)
    if not user32.SetClipboardData(fmt, handle):
        kernel32.GlobalFree(handle)


def _set_clipboard_text(text: str, transient: bool) -> bool:
    if not _open_clipboard():
        return False
    try:
        user32.EmptyClipboard()
        _put_block(CF_UNICODETEXT, (text + "\0").encode("utf-16-le"))
        if transient:
            # Keeps the dictated text out of Win+V clipboard history and cloud sync.
            for name in ("ExcludeClipboardContentFromMonitorProcessing", "CanIncludeInClipboardHistory"):
                fmt = user32.RegisterClipboardFormatW(name)
                _put_block(fmt, b"\0\0\0\0")
        return True
    finally:
        user32.CloseClipboard()


def _restore_clipboard(items: list[tuple[int, bytes]]) -> None:
    if not _open_clipboard():
        return
    try:
        user32.EmptyClipboard()
        for fmt, data in items:
            _put_block(fmt, data)
    finally:
        user32.CloseClipboard()


def copy_to_clipboard(text: str) -> None:
    if sys.platform == "win32":
        _set_clipboard_text(text, transient=False)
    else:
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(text)


# --- keystrokes --------------------------------------------------------------

def _key(vk: int = 0, scan: int = 0, flags: int = 0) -> "INPUT":
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(vk, scan, flags, 0, 0)))


def _send(events: list) -> None:
    arr = (INPUT * len(events))(*events)
    user32.SendInput(len(events), arr, ctypes.sizeof(INPUT))


def _wait_modifiers_released(timeout: float = 1.5) -> None:
    # If the user is still holding Ctrl+Shift from the hotkey, our Ctrl+V would
    # arrive as Ctrl+Shift+V. Give them a moment to let go.
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in _HELD_MODIFIERS):
            return
        time.sleep(0.02)


def _press_paste() -> None:
    _send([_key(VK_CONTROL), _key(VK_V), _key(VK_V, flags=KEYEVENTF_KEYUP), _key(VK_CONTROL, flags=KEYEVENTF_KEYUP)])


def _type_unicode(text: str) -> None:
    events = []
    for ch in text.replace("\r\n", "\n"):
        if ch == "\n":
            events += [_key(VK_RETURN), _key(VK_RETURN, flags=KEYEVENTF_KEYUP)]
            continue
        units = ch.encode("utf-16-le")
        for i in range(0, len(units), 2):  # characters outside the BMP take two units
            code = int.from_bytes(units[i : i + 2], "little")
            events += [_key(scan=code, flags=KEYEVENTF_UNICODE),
                       _key(scan=code, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)]
    for i in range(0, len(events), 200):
        _send(events[i : i + 200])
        time.sleep(0.005)


def _focus(hwnd: int) -> None:
    if hwnd and user32.IsWindow(hwnd) and foreground_window() != hwnd:
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)


def insert_text(text: str, target_hwnd: int = 0, method: str = "paste", restore: bool = True) -> None:
    """Deliver text to the focused field. Runs on a worker thread."""
    if not text:
        return
    if sys.platform != "win32":
        _insert_generic(text, method)
        return
    _wait_modifiers_released()
    _focus(target_hwnd)
    if method == "type":
        _type_unicode(text)
        return
    saved = _snapshot_clipboard() if restore else []
    if not _set_clipboard_text(text, transient=restore):
        _type_unicode(text)  # clipboard is locked by someone else
        return
    time.sleep(0.02)
    _press_paste()
    if restore:
        time.sleep(0.45)  # the target app reads the clipboard asynchronously
        _restore_clipboard(saved)


def _insert_generic(text: str, method: str) -> None:
    from pynput.keyboard import Controller, Key

    kb = Controller()
    if method == "type":
        kb.type(text)
        return
    copy_to_clipboard(text)
    modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
    with kb.pressed(modifier):
        kb.press("v")
        kb.release("v")
