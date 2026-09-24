# Changelog

## 0.2.0
- **macOS build** for Apple Silicon (`BeautifulVoice-macOS.dmg`): the shortcut and ⌘V through pynput, clipboard restore, open at login, Mac key symbols.
- **In-app updates.** The app checks for a new release at start and every six hours. A card in the sidebar offers to download it; installed Windows copies install it and restart by themselves.
- *Settings → About → Check for updates*.

## 0.1.1
- **Windows installer** (`BeautifulVoice-Setup.exe`): per-user install without an administrator prompt, Start menu and desktop shortcuts, optional autostart, uninstall from *Settings → Apps*.
- **Models without Hugging Face**: every model is mirrored in this repository's `models-v1` release; the app times both sources and downloads from the faster one.
- **Nemotron 3.5 ASR** is the default model and downloads by itself on first start.
- The interface in nine languages: English, 中文, हिन्दी, Español, Français, Português, Русский, Deutsch, 日本語.
- Half the download size: unused Qt modules are no longer shipped.

## 0.1.0
- First release: global-shortcut dictation with a focus-safe overlay, phrase-by-phrase recognition while you speak, 11 local models with accuracy and speed meters, the voice test, history with a limit, light and dark themes.
