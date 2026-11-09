"""Voices and speech end to end, with ffmpeg and a stand-in for the big voice models (the real ones are in
test_voice_models.py, run with -m slow). The stand-in "speaks" a tone of 0.05 seconds per letter and "changes
a voice" into a tone of the same length, so timings can be checked exactly."""
import json
import time
from pathlib import Path

import anyio
import numpy as np
import pytest
import soundfile
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import models, paths, progress, speech, transcribe, voices

SECONDS_PER_LETTER = 0.05


class Out:
    """Looks like the tensor Chatterbox returns: .squeeze(0).numpy()."""

    def __init__(self, audio):
        self.audio = audio

    def squeeze(self, _):
        return self

    def numpy(self):
        return self.audio


class StandIn:
    sr = 24000

    def __init__(self):
        self.texts, self.languages, self.delay = [], [], 0.0

    def prepare_conditionals(self, sample):
        assert Path(sample).name == "voice-sample.wav"

    set_target_voice = prepare_conditionals

    def generate(self, text, language_id=None):
        if text.endswith("piece.wav"):  # changing a voice: same length
            seconds = soundfile.info(text).duration
        else:
            time.sleep(self.delay)
            self.texts.append(text)
            self.languages.append(language_id)
            seconds = len(text) * SECONDS_PER_LETTER
        t = np.arange(int(seconds * self.sr)) / self.sr
        return Out((0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32))


@pytest.fixture
def stand_in(monkeypatch, with_models):
    model = StandIn()
    monkeypatch.setattr(speech, "load", lambda kind, report: model)
    monkeypatch.setattr(speech, "read_aloud", lambda text, reader, tmp: voices.read_audio(
        FIXTURES / "jfk.wav", 16000))  # the online reader voice, without the internet
    return model


FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def voice(copy_of, with_models):
    """A saved voice called "Test" (from the speech sample, looped)."""
    return voices.save_voice(progress.Job(), str(copy_of("long.mp3")), "Test", True)


def run(work, *args):
    return work(progress.Job(), *args)


def sound_starts(file):
    """Where each stretch of sound in an audio file starts, in seconds."""
    import librosa
    audio = voices.read_audio(file, 16000)
    return [a / 16000 for a, _ in librosa.effects.split(audio, top_db=30, frame_length=256, hop_length=64)]


def test_saving_voices_from_audio_and_video(copy_of, with_models):
    saved = run(voices.save_voice, str(copy_of("long.mp3")), "Anna", True)
    folder = paths.output_root() / "voices"
    assert saved == {"voice": "Anna", "sample_file": str(folder / "Anna.wav"), "seconds": 30.0}
    assert run(voices.save_voice, str(copy_of("talk.mp4")), "Anna", True)["voice"] == "Anna (2)"  # never replaced
    assert voices.list_voices() == {"voices": ["Anna", "Anna (2)"], "folder": str(folder),
                                    "kannada_sentence": voices.SENTENCE, "kannada_readings": []}
    sample = soundfile.read(voices.sample("Anna", copy_of("talk.mp3").parent))[0]
    assert len(sample) == 10 * voices.RATE and np.abs(sample).max() == pytest.approx(0.9, abs=0.01)


def test_a_file_that_is_not_audio_is_refused(tmp_path, with_models):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    with pytest.raises(ToolError, match="couldn't be read as audio"):
        run(voices.save_voice, str(tmp_path / "notes.txt"), "Me", True)
    with pytest.raises(ToolError, match="There is no file"):
        run(voices.save_voice, str(tmp_path / "missing.mp3"), "Me", True)


def test_speaking_text(stand_in, voice):
    result = run(speech.speak, "Test", "English", "little_slower", "Hello there. This is a test.")
    assert result["output_file"] == str(paths.output_root() / "Speech" / "Hello there (Test voice).mp3")  # first words
    spoken = len("Hello there. This is a test.") * SECONDS_PER_LETTER + speech.PAUSE
    assert result["seconds"] == pytest.approx(spoken / 0.9, abs=0.1)  # slowed to 0.9
    assert speech.voices.read_audio(result["output_file"], 16000).size / 16000 == pytest.approx(spoken / 0.9, abs=0.15)
    assert stand_in.languages == [None]
    elsewhere = run(speech.speak, "Test", "English", "as_made", "Hello.", None, None, str(paths.output_root() / "Mine"))
    assert elsewhere["output_file"] == str(paths.output_root() / "Mine" / "Hello (Test voice).mp3")  # a folder they named


def test_speaking_a_transcript_leaves_the_times_out(stand_in, voice, tmp_path):
    transcript = tmp_path / "Lesson (Hindi).txt"
    transcript.write_text("[0.0s] पहला वाक्य।\n[2.5s] दूसरा वाक्य।\n", encoding="utf-8")
    result = run(speech.speak, "Test", "Hindi", "as_made", None, str(transcript))
    assert result["output_file"] == str(tmp_path / "Lesson (Hindi) (Test voice).mp3")
    assert stand_in.texts == ["पहला वाक्य। दूसरा वाक्य।"] and stand_in.languages == ["hi"]
    again = run(speech.speak, "Test", "Hindi", "as_made", None, str(transcript), "Hindi reading")
    assert again["output_file"] == str(tmp_path / "Hindi reading (Test voice).mp3")


def test_pronunciations_change_what_the_voice_is_given_to_say(stand_in, voice):
    assert speech.set_pronunciations("Test", {"Madav": "Maa-dhuv"}) == {"count": 1}
    folder = paths.output_root() / "voices"
    assert (folder / "Test.pronunciations.json").is_file() and voices.list_voices()["voices"] == ["Test"]  # beside it
    result = run(speech.speak, "Test", "English", "as_made", "Madav's talk. Madavan met MADAV. Ask Madav!")
    # Whole words in any case, also with an apostrophe; part of a longer word is left alone.
    assert stand_in.texts == ["Maa-dhuv's talk. Madavan met Maa-dhuv. Ask Maa-dhuv!"]
    assert result["output_file"].endswith("Madav's talk (Test voice).mp3")  # the file is named from the words as written
    assert run(speech.speak, "Test", "English", "as_made", "Nothing to change.")["seconds"] > 0
    assert stand_in.texts[-1] == "Nothing to change."


def test_the_list_grows_changes_and_shrinks_and_serves_every_language(stand_in, voice):
    speech.set_pronunciations("Test", {"Madav": "Maa-dhuv"})
    assert speech.set_pronunciations("Test", {"Anna": "Ah-na", "madav": "Maa-dhav"}) == {"count": 2}  # one word, once
    assert speech.set_pronunciations("Test", {"ANNA": ""}) == {"count": 1}  # an empty respelling removes it
    speech.set_pronunciations("Test", {"राजू": "रा-जू", "New York": "Noo York"})
    run(speech.speak, "Test", "Hindi", "as_made", "राज और राजू और राजूजी। Visit new york today.")
    assert stand_in.texts == ["राज और रा-जू और राजूजी। Visit Noo York today."]  # not "राज" or "राजूजी": other words


def test_dubbing_uses_the_list_too(stand_in, voice, tmp_path):
    speech.set_pronunciations("Test", {"Madav": "Maa-dhuv"})
    segments = [{"start": 0.0, "end": 3.0, "text": "Madav said hello to everyone here."},
                {"start": 5.0, "end": 9.0, "text": "Then Madav went home and had some tea."}]  # 2 s apart: not joined
    file = tmp_path / "Lesson (English dubbing).segments.json"
    file.write_text(json.dumps(segments), encoding="utf-8")
    run(speech.speak_timed, str(file), "Test", "English", "as_made")
    assert stand_in.texts == ["Maa-dhuv said hello to everyone here.", "Then Maa-dhuv went home and had some tea."]


def test_pronunciations_ask_for_what_is_missing(stand_in, voice):
    with pytest.raises(ToolError, match='no saved voice called "Bob"'):
        speech.set_pronunciations("Bob", {"Madav": "Maa-dhuv"})
    with pytest.raises(ToolError, match="at least one word"):
        speech.set_pronunciations("Test", {})
    with pytest.raises(ToolError, match="needs the word as it is written"):
        speech.set_pronunciations("Test", {" ": "x"})
    assert not (paths.output_root() / "voices" / "Test.pronunciations.json").exists()  # nothing half saved


def test_kannada_is_read_by_a_reader_voice_and_changed_into_the_saved_voice(stand_in, voice):
    result = run(speech.speak, "Test", "Kannada", "as_made", "ನಮಸ್ಕಾರ.")
    assert stand_in.texts == []  # not spoken directly: the reader's audio was converted, keeping its length
    assert result["seconds"] == pytest.approx(len(voices.read_audio(FIXTURES / "jfk.wav", 16000)) / 16000, abs=0.6)
    assert result["route"] == "reader"


class IndicStandIn(StandIn):
    """IndicF5 (indic.Speaker): listens to the voice's reading of the Kannada sentence, then speaks like StandIn."""

    def prepare_conditionals(self, reading):
        self.reading = Path(reading).name


def test_kannada_is_spoken_directly_once_the_sentence_is_read(stand_in, voice, copy_of, monkeypatch):
    """With the Kannada voice set up (IndicF5 stood in for), a voice's reading of the sentence, given as a file, makes
    Kannada come straight from the voice model. Before that reading, and for Tamil always, the reader voice."""
    model = IndicStandIn()
    monkeypatch.setattr(speech.indic, "ready", lambda: True)
    monkeypatch.setattr(speech.indic, "load", lambda report: model)
    assert run(speech.speak, "Test", "Kannada", "as_made", "ನಮಸ್ಕಾರ.")["route"] == "reader"
    saved = run(voices.save_voice, str(copy_of("talk.mp3")), "Test", True, True)  # 11 s: the sentence and a little
    assert saved["kannada_reading"] == str(paths.output_root() / "voices" / "Test.kannada.flac")
    text = voices.SENTENCE
    result = run(speech.speak, "Test", "Kannada", "as_made", text)
    assert result["route"] == "direct" and model.reading == "Test.kannada.flac" and model.texts == [text]
    assert result["seconds"] == pytest.approx(len(text) * SECONDS_PER_LETTER + speech.PAUSE, abs=0.1)
    assert run(speech.speak, "Test", "Tamil", "as_made", "வணக்கம்.")["route"] == "reader"
    assert model.texts == [text]


def test_dubbing_puts_every_line_at_its_time(stand_in, voice, tmp_path):
    segments = [{"start": 0.0, "end": 0.4, "text": "…"},  # no words (music, sound effects): stays silent
                {"start": 0.5, "end": 2.0, "text": "a" * 39 + "."},  # 2.0 s spoken, 2.5 s until the next: slowed to 0.9
                {"start": 3.0, "end": 4.5, "text": "b" * 43 + "."},  # 2.2 s in 2 s: sped up to 1.1, ends at 5.0
                {"start": 5.0, "end": 6.0, "text": "c" * 39 + "."},  # 2.0 s in 1.5 s: 1.15 at most, so 0.24 s over
                {"start": 6.5, "end": 9.0, "text": "d" * 9 + "."}]  # starts late, right after the line before
    file = tmp_path / "Lesson (Hindi).segments.json"
    file.write_text(json.dumps(segments), encoding="utf-8")
    result = run(speech.speak_timed, str(file), "Test", "Hindi", "little_slower")
    assert result["output_file"] == str(tmp_path / "Lesson (Hindi) (Test voice).mp3")
    assert result["lines"] == 4 and result["overrun_count"] == 1 and result["route"] == "direct"
    assert result["overruns"] == [{"at": "0:05", "over_by": 0.2}] and result["most_late"] == 0.2
    assert result["seconds"] == pytest.approx(5.0 + 2.0 / 1.15 + 0.5 / 0.9, abs=0.05)
    starts = sound_starts(result["output_file"])
    assert len(starts) == 2  # silence before the first line and between the first two; then line after line
    assert starts[0] == pytest.approx(0.5, abs=0.05) and starts[1] == pytest.approx(3.0, abs=0.05)


def test_changing_a_voice_keeps_the_length(stand_in, voice, copy_of):
    audio = copy_of("long.mp4")  # a video: its sound is used
    result = run(speech.change_voice, str(audio), "Test", "as_made")
    assert result["output_file"] == str(audio.parent / "long (Test voice).mp3")
    assert result["seconds"] == pytest.approx(110, abs=0.2)


def test_an_unknown_voice_or_language(stand_in, voice):
    with pytest.raises(ToolError, match='no saved voice called "Bob"'):
        run(speech.speak, "Bob", "English", "as_made", "Hello.")
    with pytest.raises(ToolError, match="German can't be spoken yet"):
        run(speech.speak, "Test", "German", "as_made", "Hallo.")
    with pytest.raises(ToolError, match="no words to read aloud"):
        run(speech.speak, "Test", "English", "as_made", "  ")


def test_stopping_speech_leaves_no_file(stand_in, voice):
    stand_in.delay = 0.3  # each piece takes a moment, like the real model
    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if "2 of" in message:
                        scope.cancel()
            await progress.run(Ctx(), speech.speak, "Test", "English", "as_made", "One. " * 400)

    anyio.run(main)
    assert not (paths.output_root() / "Speech").exists() or not list((paths.output_root() / "Speech").iterdir())


def test_tempo_changes_the_length_not_the_pitch(with_models):
    t = np.arange(24000 * 4) / 24000
    tone = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    faster = speech.tempo(tone, 24000, 1.15)
    assert len(faster) / 24000 == pytest.approx(4 / 1.15, abs=0.05)
    spectrum = np.abs(np.fft.rfft(faster))
    assert np.fft.rfftfreq(len(faster), 1 / 24000)[spectrum.argmax()] == pytest.approx(440, abs=3)


def test_transcribing_lets_a_voice_model_go_first(with_models, monkeypatch):
    monkeypatch.setattr(models, "loaded", {"multilingual": "a voice model of several GB"})
    monkeypatch.setattr(transcribe.gpu, "usable", lambda: False)  # this PC may have a card; CI hasn't
    transcribe.load("base", progress.Job())
    assert list(models.loaded) == [("base", "cpu")]


def test_a_second_voice_or_transcript_job_waits_for_the_first(with_models):
    with models.one_at_a_time(progress.Job()):
        waiting = progress.Job()
        waiting.stop.set()  # Esc while it waits: it stops at once, without starting
        with pytest.raises(progress.Stopped):
            with models.one_at_a_time(waiting):
                pass
    with models.one_at_a_time(progress.Job()):  # free again once the first job is done
        pass
