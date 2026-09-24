import json

import numpy as np
import pytest

from beautiful_voice.config import Settings, SettingsStore
from beautiful_voice.dictation import _is_hallucination, join_phrases
from beautiful_voice.history import History, HistoryEntry
from beautiful_voice.hotkeys import parse_combo
from beautiful_voice.i18n import STRINGS
from beautiful_voice.metrics import accuracy_from_wer, cer, normalize, speed_score, wer
from beautiful_voice.models.catalog import CATALOG, RECOMMENDED, by_id
from beautiful_voice.models.download import RemoteFile, select_files
from beautiful_voice.segmenter import SAMPLE_RATE, Segmenter, split_offline


# --- metrics ---------------------------------------------------------------

def test_wer_ignores_case_punctuation_and_yo():
    assert wer("Привет, ёжик!", "привет ежик") == 0.0
    assert wer("Hello there.", "hello there") == 0.0


def test_wer_counts_substitutions_insertions_deletions():
    assert wer("a b c d", "a x c d") == pytest.approx(0.25)
    assert wer("a b c d", "a b c d e") == pytest.approx(0.25)
    assert wer("a b c d", "a c d") == pytest.approx(0.25)


def test_numbers_as_words_or_digits_match():
    assert wer("в десять утра", "в 10 утра") == 0.0


def test_cer_and_accuracy():
    assert cer("кот", "кит") == pytest.approx(1 / 3)
    assert accuracy_from_wer(0.052) == pytest.approx(94.8)
    assert accuracy_from_wer(1.7) == 0.0


def test_speed_score_is_log_scaled_and_clamped():
    assert speed_score(0.5) == 0.0
    assert speed_score(10) == pytest.approx(0.5)
    assert speed_score(100) == pytest.approx(1.0)
    assert speed_score(5000) == 1.0


def test_normalize_splits_hyphens():
    assert normalize("наконец-то") == ["наконец", "то"]


# --- segmenter -------------------------------------------------------------

def _tone(seconds, amp=0.2, freq=220.0):
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _silence(seconds, amp=0.0005):
    rng = np.random.default_rng(1)
    return (rng.standard_normal(int(seconds * SAMPLE_RATE)) * amp).astype(np.float32)


def test_segmenter_cuts_at_pause_after_min_length():
    audio = np.concatenate([_silence(0.3), _tone(3.5), _silence(0.8), _tone(2.0), _silence(0.3)])
    seg = Segmenter()
    parts = []
    for i in range(0, len(audio), 480):  # feed in 30 ms blocks like the microphone does
        parts += seg.feed(audio[i : i + 480])
    tail = seg.flush()
    assert len(parts) == 1
    assert parts[0].has_speech
    first = len(parts[0].audio) / SAMPLE_RATE
    assert 3.8 < first < 4.7  # the cut lands inside the pause
    assert tail is not None and tail.has_speech
    assert len(parts[0].audio) + len(tail.audio) == len(audio)


def test_segmenter_does_not_cut_short_phrases():
    audio = np.concatenate([_tone(1.0), _silence(0.6), _tone(1.0)])
    assert len(split_offline(audio)) == 1


def test_segmenter_forces_cut_on_long_speech():
    audio = _tone(30.0)
    parts = split_offline(audio)
    assert len(parts) >= 2
    assert all(len(p.audio) / SAMPLE_RATE <= 24.1 for p in parts)
    assert sum(len(p.audio) for p in parts) == len(audio)


def test_silence_is_not_speech():
    parts = split_offline(_silence(2.0))
    assert parts and not any(p.has_speech for p in parts)


# --- history ---------------------------------------------------------------

def test_history_keeps_only_the_limit_and_totals(tmp_path):
    h = History(limit=3, path=tmp_path / "h.json")
    for i in range(5):
        h.add(HistoryEntry(text=f"entry {i} two words", duration=2.0, model="m"))
    assert [e.text.split()[1] for e in h.entries] == ["4", "3", "2"]
    assert h.totals.dictations == 5
    assert h.totals.words == 20
    again = History(limit=3, path=tmp_path / "h.json")
    assert len(again.entries) == 3 and again.totals.dictations == 5


def test_history_limit_shrinks(tmp_path):
    h = History(limit=10, path=tmp_path / "h.json")
    for i in range(6):
        h.add(HistoryEntry(text=str(i), duration=1, model="m"))
    dropped = h.set_limit(2)
    assert len(dropped) == 4 and len(h.entries) == 2


def test_history_delete_and_clear(tmp_path):
    h = History(limit=10, path=tmp_path / "h.json")
    e = HistoryEntry(text="x", duration=1, model="m")
    h.add(e)
    assert h.delete(e.id) and not h.entries
    h.add(HistoryEntry(text="y", duration=1, model="m"))
    h.clear()
    assert not h.entries


# --- settings --------------------------------------------------------------

def test_settings_roundtrip_and_types(tmp_path):
    path = tmp_path / "s.json"
    store = SettingsStore(path)
    assert store.set("history_limit", "25")
    assert store.get("history_limit") == 25
    assert not store.set("history_limit", 25)  # unchanged
    store.set("sounds", 0)
    assert SettingsStore(path).get("sounds") is False
    path.write_text(json.dumps({"history_limit": "oops", "unknown": 1}))
    assert SettingsStore(path).get("history_limit") == Settings().history_limit


# --- hotkeys ---------------------------------------------------------------

def test_parse_combo():
    c = parse_combo("Shift+Ctrl+Space")
    assert c.modifiers == ("ctrl", "shift") and c.key == "space" and c.vk == 0x20
    assert parse_combo("f9").key == "f9"
    assert parse_combo("cmd+alt+d").modifiers == ("alt", "win")
    for bad in ("ctrl", "ctrl+a+b", "a", "ctrl+nosuchkey"):
        with pytest.raises(ValueError):
            parse_combo(bad)


# --- dictation helpers -----------------------------------------------------

def test_join_phrases_and_hallucinations():
    assert join_phrases(["Привет", " ", "как дела ?"]) == "Привет как дела?"
    assert _is_hallucination("Продолжение следует...")
    assert not _is_hallucination("Продолжение следует завтра")


# --- catalog / downloads ---------------------------------------------------

def test_catalog_is_consistent():
    ids = [s.id for s in CATALOG]
    assert len(ids) == len(set(ids))
    assert by_id(RECOMMENDED) is not None
    for s in CATALOG:
        assert s.backend in {"faster-whisper", "onnx-asr", "sherpa-onnx"}
        assert 1 <= s.speed_tier <= 5 and s.include
        assert s.backend != "onnx-asr" or s.onnx_name


def test_select_files_by_pattern():
    files = [RemoteFile(p, 1) for p in (
        "config.json", "vocab.txt", "encoder-model.onnx", "encoder-model.onnx.data",
        "encoder-model.int8.onnx", "decoder_joint-model.int8.onnx", "nemo128.onnx", "README.md")]
    spec = by_id("parakeet-tdt-0.6b-v3")
    chosen = sorted(f.path for f in select_files(files, spec.include))
    assert chosen == ["config.json", "decoder_joint-model.int8.onnx", "encoder-model.int8.onnx", "vocab.txt"]


def test_translations_have_the_same_keys():
    assert set(STRINGS["en"]) == set(STRINGS["ru"])
