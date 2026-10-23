"""The parts of keeping a dub's music that need no model: where the original sound stays, and one big model in
memory at a time."""
import pytest

from video_audio_engine import models, progress, music


def at(keep, seconds):
    return float(keep[int(seconds * music.RATE)])


def test_the_original_sound_stays_outside_the_spoken_lines():
    keep = music.kept([{"start": 1.0, "end": 2.0, "text": "Hello"}], 4 * music.RATE)
    assert at(keep, 0.4) == 1 and at(keep, 3.0) == 1  # well before and after the line
    assert at(keep, 0.75) == 0 and at(keep, 1.5) == 0 and at(keep, 2.25) == 0  # the line, and PAD around it
    assert at(keep, 0.625) == pytest.approx(0.5, abs=0.01) and at(keep, 2.375) == pytest.approx(0.5, abs=0.01)


def test_a_short_pause_between_lines_stays_mostly_without_the_voice():
    """A pause too short to fade the original in and out again: its voice must not come back for a moment."""
    lines = [{"start": 1.0, "end": 2.0, "text": "One."}, {"start": 2.6, "end": 3.0, "text": "Two."}]
    keep = music.kept(lines, 4 * music.RATE)
    assert keep[int(2.0 * music.RATE):int(2.6 * music.RATE)].max() <= 0.21


def test_lines_at_the_very_start_and_past_the_end():
    keep = music.kept([{"start": 0.0, "end": 0.5, "text": "Hi."}, {"start": 9.0, "end": 9.5, "text": "Bye."}],
                      2 * music.RATE)
    assert at(keep, 0.0) == 0 and at(keep, 1.5) == 1 and len(keep) == 2 * music.RATE


def test_the_music_keeper_lets_the_voice_model_go_first(monkeypatch):
    import demucs.hf

    class Model:
        def eval(self):
            return "HTDemucs"

    monkeypatch.setattr(demucs.hf, "load_safetensors_model", lambda path: Model())
    monkeypatch.setattr(models, "ensure", lambda names, report: None)
    monkeypatch.setattr(models, "loaded", {"multilingual": "a voice model of several GB"})
    assert music.load(progress.Job().report) == "HTDemucs" and models.loaded == {"music": "HTDemucs"}
