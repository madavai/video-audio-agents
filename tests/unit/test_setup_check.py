"""check_setup's graphics card and speaker labels, with the card's answers made up (CI has no card)."""
import subprocess

import pytest

from video_audio_engine import gpu, setup_check, speakers

CARD = "NVIDIA GeForce RTX 5090 Laptop GPU"


@pytest.fixture
def card(monkeypatch):
    """Sets what the computer has: the card's name (or None), the graphics-card option, whether CUDA works."""
    def have(name, installed=False, works=False):
        monkeypatch.setattr(gpu, "card", lambda: name)
        monkeypatch.setattr(gpu, "installed", lambda: installed)
        monkeypatch.setattr(gpu, "usable", lambda: bool(name and installed and works))
    monkeypatch.setattr(gpu, "failed", None)
    return have


def graphics_notes(result):
    return [note for note in result["notes"] if "graphics card" in note]


def test_no_card_no_note(card):
    card(None)
    result = setup_check.check_setup()
    assert result["gpu"] is None and result["gpu_usable"] is False and graphics_notes(result) == []


def test_a_card_without_the_option_suggests_it(card):
    card(CARD)
    result = setup_check.check_setup()
    assert result["gpu"] == CARD and result["gpu_usable"] is False
    assert graphics_notes(result) == [f'An NVIDIA graphics card was found ({CARD}): "set up the graphics card" '
                                      "(a 0.6 GB download) makes transcripts several times faster."]
    assert "later version" not in str(result)


def test_a_card_that_doesnt_work_says_so(card):
    card(CARD, installed=True)
    assert graphics_notes(setup_check.check_setup()) == [
        f"The graphics card ({CARD}) can't be used right now, so transcripts run on the processor."]


def test_a_working_card_needs_no_note(card):
    card(CARD, installed=True, works=True)
    result = setup_check.check_setup()
    assert result["gpu_usable"] is True and graphics_notes(result) == []


def test_the_card_is_named_by_nvidia_smi(monkeypatch):
    gpu.card.cache_clear()
    monkeypatch.setattr(gpu.shutil, "which", lambda name: "nvidia-smi.exe")
    monkeypatch.setattr(gpu.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, f"{CARD}\n", ""))
    try:
        assert gpu.card() == CARD
    finally:
        gpu.card.cache_clear()


def test_after_a_failure_the_card_isnt_tried_again(monkeypatch):
    monkeypatch.setattr(gpu, "card", lambda: CARD)
    monkeypatch.setattr(gpu, "libraries_found", lambda: True)
    monkeypatch.setattr(gpu, "failed", None)
    note = gpu.give_up(RuntimeError("Library cublas64_12.dll is not found or cannot be loaded"))
    assert note == "The graphics card couldn't be used this time, so this ran on the processor (slower)."
    assert gpu.failed.startswith("Library cublas64_12.dll") and gpu.usable() is False


def test_without_the_option_the_libraries_arent_looked_for():
    assert gpu.installed() is False  # the tests' environment is the standard setup
    assert gpu.libraries_found() is False


def test_speaker_labels_arent_ready_in_the_standard_setup(private_data):
    assert speakers.ready() is False
    assert setup_check.check_setup()["speaker_labels"] is False
