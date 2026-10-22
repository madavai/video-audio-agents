"""The real voice models, on this computer only: `uv run pytest -m slow`, with the Chatterbox files in
engine/.test-data/models/chatterbox (setup "with voice" downloads them; copy or link them there). Needs the internet
for the reader voices. The saved voice is a Microsoft reader voice, so no real person's voice is copied."""
import asyncio
import json

import numpy as np
import psutil
import pytest

from video_audio_engine import models, progress, speech, transcribe, voices

pytestmark = pytest.mark.slow
SENTENCES = ("The garden behind the old library opens at nine every morning. Children come to read under the trees, "
             "and the gardener waters the roses before the sun gets too hot. On Sundays there is music by the "
             "fountain, and people bring tea and biscuits to share with their neighbours. In the autumn the leaves "
             "turn gold and red, and the whole street smells of apples from the market on the corner.")


def run(work, *args):
    return work(progress.Job(), *args)


def reader_says(text, reader, file):
    """A clean recording of a Microsoft reader voice saying `text` (needs the internet)."""
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, reader).save(str(file)))
    return file


@pytest.fixture
def reader_voice(with_models, tmp_path):
    """A saved voice called "Reader": about 20 seconds of a Microsoft reader voice, saved like an upload."""
    return run(voices.save_voice, str(reader_says(SENTENCES, "en-GB-RyanNeural", tmp_path / "ryan.mp3")), "Reader", True)


def similarity(a, b):
    """How alike two voices sound (16 kHz audio), by Chatterbox's own voice encoder: 1 is the same voice."""
    from chatterbox.models.voice_encoder import VoiceEncoder
    from safetensors.torch import load_file
    encoder = VoiceEncoder()
    encoder.load_state_dict(load_file(models.folder("english") / "ve.safetensors"))
    encoder.eval()
    x, y = (encoder.embeds_from_wavs([audio], 16000, as_spk=True) for audio in (a, b))
    return float(x @ y)


def test_speak_english_one_sentence(reader_voice, tmp_path):
    result = run(speech.speak, "Reader", "English", "little_slower", "The quick brown fox jumps over the lazy dog.")
    assert 2 < result["seconds"] < 8
    heard = run(transcribe.transcribe, result["output_file"], "fast", True)
    text = open(heard["transcript_file"], encoding="utf-8").read().lower()
    assert all(word in text for word in ("quick", "brown", "fox", "lazy", "dog")), text


def test_change_voice_keeps_the_length_and_sounds_like_the_saved_voice(reader_voice, tmp_path):
    # A clean recording of another voice. (On the old 1961 speech sample the match measures about 0.8: the old
    # recording's sound carries over.)
    source = reader_says("And so, my fellow Americans, ask not what your country can do for you. Ask what you can do "
                         "for your country. We choose to go to the Moon in this decade.", "en-US-GuyNeural",
                         tmp_path / "guy.mp3")
    result = run(speech.change_voice, str(source), "Reader", "as_made")
    before, after = voices.read_audio(source, 16000), voices.read_audio(result["output_file"], 16000)
    assert len(after) / 16000 == pytest.approx(len(before) / 16000, abs=0.1)
    target = voices.read_audio(voices.voice_file("Reader"), 16000)
    assert similarity(after, target) >= 0.85  # the same voice measures about 0.95, two different voices 0.6 to 0.75
    assert similarity(after, target) > similarity(before, target) + 0.1


def test_dubbing_three_hindi_lines_each_start_within_a_fifth_of_a_second(reader_voice, tmp_path):
    import librosa
    lines = [{"start": 0.5, "end": 3.0, "text": "नमस्ते दोस्तों।"}, {"start": 4.0, "end": 6.5, "text": "आज मौसम अच्छा है।"},
             {"start": 8.0, "end": 10.5, "text": "धन्यवाद।"}]
    file = tmp_path / "Talk (Hindi).segments.json"
    file.write_text(json.dumps(lines, ensure_ascii=False), encoding="utf-8")
    result = run(speech.speak_timed, str(file), "Reader", "Hindi", "little_slower")
    assert result["overruns"] == []
    audio = voices.read_audio(result["output_file"], 16000)
    starts = [a / 16000 for a, _ in librosa.effects.split(audio, top_db=35, frame_length=256, hop_length=64)]
    for line in lines:
        first_sound = min(starts, key=lambda s: abs(s - line["start"]))
        assert abs(first_sound - line["start"]) <= 0.2, (line, starts)


def test_speak_kannada_through_the_reader_voice(reader_voice):
    result = run(speech.speak, "Reader", "Kannada", "little_slower", "ನಮಸ್ಕಾರ. ಇಂದು ಹವಾಮಾನ ಚೆನ್ನಾಗಿದೆ.")
    assert 1.5 < result["seconds"] < 10


def test_one_big_model_in_memory_at_a_time(with_models):
    process, report = psutil.Process(), progress.Job().report
    speech.load("english", report)
    with_english = process.memory_info().rss
    speech.load("multilingual", report)
    assert list(models.loaded) == ["multilingual"]
    # Both together would be about 3 GB more; letting the English one go keeps memory about the same.
    assert process.memory_info().rss - with_english < 1.5 * 1024**3
