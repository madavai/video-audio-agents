"""The voice rules that need no model: text pieces, cut points, the 10-second sample, dubbing timing, speeds,
language routing, consent, recording, and one big model in memory at a time."""
import sys
import types

import numpy as np
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import models, progress, speech, voices

RATE = 16000


def speechlike(seconds, rate=RATE, loudness=0.5):
    """A stand-in for speech: a tone that swells and fades four times a second, without pauses."""
    t = np.arange(int(seconds * rate)) / rate
    return (loudness * np.sin(2 * np.pi * 220 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)


def test_text_pieces_are_sentences_of_at_most_300_characters():
    text = " ".join(f"This is sentence number {i}, which is about fifty letters." for i in range(40))
    pieces = speech.text_pieces(text)
    assert all(len(p) <= 300 for p in pieces) and len(pieces) > 5
    assert all(p.endswith(".") for p in pieces)  # cut between sentences, not inside them
    assert " ".join(pieces) == text
    long_sentence = "word " * 200  # 1000 characters without a full stop: split at spaces
    assert all(len(p) <= 300 for p in speech.text_pieces(long_sentence))
    assert speech.text_pieces("पहला वाक्य। दूसरा वाक्य।", limit=12) == ["पहला वाक्य।", "दूसरा वाक्य।"]  # Hindi full stop


def test_times_and_markdown_are_not_read_aloud():
    assert speech.plain_text("[0.0s] Hello there.\n[2.5s] How are you?\n") == "Hello there. How are you?"
    assert speech.plain_text("# Summary\n\n- **First** point\n- Second point.\n") == "Summary. First point. Second point."
    assert speech.plain_text("   \n") == ""


def test_long_audio_is_cut_at_quiet_moments_in_pieces_of_at_most_20_seconds():
    # 50 seconds: talking in 7-second stretches with a second of quiet between them.
    audio = np.concatenate([np.concatenate([speechlike(7), np.zeros(RATE, np.float32)]) for _ in range(6)])[:50 * RATE]
    cuts = speech.cut_points(audio, RATE)
    assert cuts[0] == 0 and cuts[-1] == len(audio)
    assert all(0 < b - a <= 20 * RATE for a, b in zip(cuts, cuts[1:]))
    for cut in cuts[1:-1]:  # each cut falls in a quiet second
        assert cut % (8 * RATE) >= 7 * RATE
    talking = speechlike(45)  # no pause at all: still pieces of at most 20 seconds
    cuts = speech.cut_points(talking, RATE)
    assert len(cuts) >= 4 and all(b - a <= 20 * RATE for a, b in zip(cuts, cuts[1:]))
    assert speech.cut_points(speechlike(5), RATE) == [0, 5 * RATE]


def test_the_voice_sample_is_the_clearest_10_seconds_and_skips_a_quiet_start():
    audio = np.concatenate([speechlike(8, loudness=0.01), speechlike(12, loudness=0.5)])
    best = voices.best_window(audio, RATE, 10)
    assert len(best) == 10 * RATE
    assert np.abs(best[:RATE]).max() > 0.4  # it starts in the loud part
    assert len(voices.best_window(audio[:5 * RATE], RATE, 10)) == 5 * RATE  # shorter than 10 seconds: all of it


def test_speeds():
    assert speech.SPEEDS == {"little_slower": 0.9, "slower": 0.8, "as_made": 1.0}


def test_dubbing_lines_start_at_their_time_and_are_sped_up_at_most_115_percent():
    segments = [{"start": 0, "end": 3, "text": "a"}, {"start": 4, "end": 7, "text": "b"},
                {"start": 8, "end": 9, "text": "c"}, {"start": 10, "end": 12, "text": "d"}]
    # Line 1 fits even slowed; line 2 fits when sped up a little; line 3 can't fit; line 4 starts late because of it.
    timing, overruns = speech.place(segments, [3.0, 4.2, 3.0, 1.0], 0.9)
    tempos, starts = [t for t, _ in timing], [at for _, at in timing]
    assert tempos[0] == 0.9 and starts[0] == 0
    assert tempos[1] == pytest.approx(4.2 / 4) and starts[1] == 4
    assert tempos[2] == 1.15 and starts[2] == 8
    assert starts[3] == pytest.approx(8 + 3.0 / 1.15)  # right after the line that ran long, never on top of it
    assert all(t <= 1.15 for t in tempos)
    assert overruns == [{"at": "0:08", "over_by": round(8 + 3.0 / 1.15 - 10, 1)}]


def test_only_the_six_languages_and_the_right_model_for_each(monkeypatch):
    with pytest.raises(ToolError, match="can't be spoken yet"):
        speech.check_language("German")
    used = []

    class Model:
        sr = 24000

        def prepare_conditionals(self, sample):
            pass

        set_target_voice = prepare_conditionals

        def generate(self, text, language_id=None):
            used.append(language_id)
            return types.SimpleNamespace(squeeze=lambda _: types.SimpleNamespace(numpy=lambda: np.ones(10, np.float32)))

    monkeypatch.setattr(speech, "load", lambda kind, report: used.append(kind) or Model())
    monkeypatch.setattr(speech, "reader_for", lambda language, sample: speech.READERS[language][0])
    monkeypatch.setattr(speech, "read_aloud", lambda text, reader, tmp: used.append(reader) or speechlike(1))
    report = progress.Job().report
    for language in ["English", "Hindi", "French", "Spanish", "Kannada", "Tamil"]:
        speech.spoken(report, ["Hello."], language, "sample.wav", "Speaking")
    assert used == ["english", None, "multilingual", "hi", "multilingual", "fr", "multilingual", "es",
                    "voice", "kn-IN-GaganNeural", None, "voice", "ta-IN-ValluvarNeural", None]


def test_no_voice_is_saved_without_consent(tmp_path):
    with pytest.raises(ToolError, match="own, or they agreed"):
        voices.save_voice(progress.Job(), str(tmp_path / "me.mp3"), "Me", False)
    with pytest.raises(ToolError, match="own, or they agreed"):
        voices.record_voice(progress.Job(), "Me", 20, False)
    assert voices.list_voices()["voices"] == []


def fake_microphone(monkeypatch, audio):
    """sounddevice replaced: the "microphone" hears `audio`, then silence."""
    class InputStream:
        def __init__(self, **kwargs):
            self.heard = np.concatenate([audio, np.zeros(120 * voices.RATE, np.float32)])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, frames):
            chunk, self.heard = self.heard[:frames], self.heard[frames:]
            return chunk[:, None], False

    monkeypatch.setitem(sys.modules, "sounddevice", types.SimpleNamespace(InputStream=InputStream,
                                                                          PortAudioError=OSError))


def test_recording_a_voice_starts_when_the_person_starts_speaking(monkeypatch):
    fake_microphone(monkeypatch, np.concatenate([np.zeros(5 * voices.RATE, np.float32), speechlike(25, voices.RATE)]))
    saved = voices.record_voice(progress.Job(), "My voice", 20, True)
    assert saved["voice"] == "My voice" and saved["seconds"] == pytest.approx(20, abs=0.3)  # 20 s from the first word
    assert voices.record_voice(progress.Job(), "My voice", 20, True)["voice"] == "My voice (2)"  # never replaced
    assert voices.list_voices()["voices"] == ["My voice", "My voice (2)"]


def test_a_silent_or_short_recording_is_refused(monkeypatch):
    fake_microphone(monkeypatch, np.zeros(30 * voices.RATE, np.float32))
    with pytest.raises(ToolError, match="Nothing was heard for a minute"):
        voices.record_voice(progress.Job(), "Me", 20, True)
    fake_microphone(monkeypatch, np.concatenate([speechlike(6, voices.RATE), np.zeros(24 * voices.RATE, np.float32)]))
    with pytest.raises(ToolError, match="only 6 seconds of speaking"):
        voices.record_voice(progress.Job(), "Me", 30, True)
    assert voices.list_voices()["voices"] == []


def test_stopping_a_recording_saves_nothing(monkeypatch):
    fake_microphone(monkeypatch, speechlike(30, voices.RATE))
    job = progress.Job()
    job.stop.set()
    with pytest.raises(progress.Stopped):
        voices.record_voice(job, "Me", 20, True)
    assert voices.list_voices()["voices"] == []


def test_an_unknown_voice_names_the_saved_ones(monkeypatch):
    fake_microphone(monkeypatch, speechlike(20, voices.RATE))
    voices.record_voice(progress.Job(), "Anna", 20, True)
    with pytest.raises(ToolError, match='no saved voice called "Bob". The saved voices are: Anna.'):
        voices.voice_file("Bob")


def test_one_big_model_in_memory_at_a_time(monkeypatch):
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from chatterbox.tts import ChatterboxTTS
    from chatterbox.vc import ChatterboxVC
    for cls in (ChatterboxVC, ChatterboxTTS, ChatterboxMultilingualTTS):
        monkeypatch.setattr(cls, "from_local", classmethod(lambda cls, folder, device: cls.__name__))
    monkeypatch.setattr(models, "ensure", lambda names, report: None)
    monkeypatch.setattr(models, "loaded", {"small": "speech-to-text"})
    report = progress.Job().report
    assert speech.load("english", report) == "ChatterboxTTS" and models.loaded == {"english": "ChatterboxTTS"}
    assert speech.load("multilingual", report) == "ChatterboxMultilingualTTS"
    assert models.loaded == {"multilingual": "ChatterboxMultilingualTTS"}
    assert speech.load("voice", report) == "ChatterboxVC" and list(models.loaded) == ["voice"]
