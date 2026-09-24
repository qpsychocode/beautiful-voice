"""Small Windows touches: a title bar that matches the theme, and an overlay
window that can be clicked without stealing focus from the app you're typing in."""

from __future__ import annotations

import sys

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008


def _colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r | (g << 8) | (b << 16)


def style_title_bar(window, dark: bool, caption: str, text: str) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    hwnd = int(window.winId())
    dwm = ctypes.windll.dwmapi
    for attr, value in ((DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark)),
                        (DWMWA_CAPTION_COLOR, _colorref(caption)),
                        (DWMWA_TEXT_COLOR, _colorref(text))):
        val = ctypes.c_int(value)
        dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))


def make_no_activate(window) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    user32 = ctypes.windll.user32
    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
    hwnd = int(window.winId())
    style = user32.GetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW | WS_EX_TOPMOST)
