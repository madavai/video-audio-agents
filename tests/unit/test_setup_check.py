from video_audio_engine import setup_check


def test_the_graphics_card_note_promises_no_version(monkeypatch):
    """Each phase has its own number now, so the note says "a later version", not which one."""
    monkeypatch.setattr(setup_check.shutil, "which", lambda name: "nvidia-smi" if name == "nvidia-smi" else None)
    result = setup_check.check_setup()
    note = next(note for note in result["notes"] if "graphics card" in note)
    assert note == "An NVIDIA graphics card was found; using it to go faster comes in a later version."
    assert result["gpu"] is True
