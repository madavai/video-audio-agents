"""The real Kannada voice model, IndicF5, on this computer only: `uv run --extra indic pytest -m slow`, with IndicF5's
two files in .test-data/models/IndicF5/ (copy them from a data folder where "set up the Kannada voice" ran: the model
is gated, so tests can't download it), Chatterbox's voice encoder in .test-data/models/chatterbox/ (to measure
likeness) and the accurate speech-to-text model in .test-data/models/faster-whisper-large-v3-turbo/ (it checks the
reading). Needs the internet for the reader voices. The saved voice is a Microsoft reader voice, so no real person's
voice is copied."""
import asyncio

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import indic, models, progress, speech, voices

pytestmark = pytest.mark.slow
# "Bengaluru is the capital of Karnataka. Many people live in this city, and every day new companies start here. In the
# evening the parks fill with children. In the rainy season the city looks green." About 13 seconds: a voice needs 10.
PASSAGE = ("ಬೆಂಗಳೂರು ಕರ್ನಾಟಕದ ರಾಜಧಾನಿ. ಈ ನಗರದಲ್ಲಿ ಅನೇಕ ಜನರು ವಾಸಿಸುತ್ತಾರೆ, ಮತ್ತು ಪ್ರತಿದಿನ ಇಲ್ಲಿ ಹೊಸ ಕಂಪನಿಗಳು "
           "ಆರಂಭವಾಗುತ್ತವೆ. ಸಂಜೆ ಉದ್ಯಾನವನಗಳು ಮಕ್ಕಳಿಂದ ತುಂಬಿರುತ್ತವೆ. ಮಳೆಗಾಲದಲ್ಲಿ ನಗರವು ಹಸಿರಾಗಿ ಕಾಣುತ್ತದೆ.")
TEXT = "ನಮಸ್ಕಾರ. ನಾಳೆ ಬೆಳಿಗ್ಗೆ ನಾವು ಮಾರುಕಟ್ಟೆಗೆ ಹೋಗಿ ತರಕಾರಿ ಮತ್ತು ಹಣ್ಣುಗಳನ್ನು ಕೊಳ್ಳೋಣ."


def run(work, *args):
    return work(progress.Job(), *args)


def reader_says(text, reader, file):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, reader).save(str(file)))
    return file


@pytest.fixture
def kannada_voice(with_models, tmp_path):
    """A saved voice "Sapna" (a Microsoft Kannada reader voice) with its reading of the Kannada sentence. Another
    Kannada sentence, read in the same voice, is refused as its reading: speech recognition hears other words."""
    if not indic.installed() or not all(models.is_present(name) for name in ("kannada", "english", "large-v3-turbo")):
        pytest.skip("needs --extra indic, and IndicF5's, Chatterbox's and large-v3-turbo's files in .test-data/models")
    run(voices.save_voice, str(reader_says(PASSAGE, "kn-IN-SapnaNeural", tmp_path / "passage.mp3")), "Sapna", True)
    other = reader_says(TEXT, "kn-IN-SapnaNeural", tmp_path / "other.mp3")  # it too starts "ನಮಸ್ಕಾರ"
    with pytest.raises(ToolError, match="doesn't sound like the Kannada sentence"):
        run(voices.save_voice, str(other), "Sapna", True, True)
    reading = reader_says(voices.SENTENCE, "kn-IN-SapnaNeural", tmp_path / "sentence.mp3")
    assert 3 <= run(voices.save_voice, str(reading), "Sapna", True, True)["seconds"] <= 15
    return tmp_path


def likeness(a, b):
    """How alike two voices sound (files), by Chatterbox's voice encoder: 1 is the same voice."""
    from chatterbox.models.voice_encoder import VoiceEncoder
    from safetensors.torch import load_file
    encoder = VoiceEncoder()
    encoder.load_state_dict(load_file(models.folder("english") / "ve.safetensors"))
    encoder.eval()
    x, y = (encoder.embeds_from_wavs([voices.read_audio(f, 16000)], 16000, as_spk=True) for f in (a, b))
    return float(x @ y)


def test_kannada_is_spoken_directly_in_the_saved_voice(kannada_voice, capsys, monkeypatch):
    monkeypatch.setattr(indic, "ready", lambda: True)  # the key isn't needed: the files are here
    stopped, last = progress.Job(), []

    def esc_in_the_take(percent, message):  # Esc once IndicF5 has started on the take
        last[:] = [percent, message]
        if message.startswith("Speaking") and percent > 0:
            stopped.stop.set()
        stopped.check()

    monkeypatch.setattr(stopped, "report", esc_in_the_take)
    with pytest.raises(progress.Stopped):
        speech.speak(stopped, "Sapna", "Kannada", "as_made", voices.SENTENCE)
    assert 0 < last[0] < 100, last  # it stopped part-way through the take, not after it
    result = run(speech.speak, "Sapna", "Kannada", "as_made", TEXT)  # the next take is right: nothing kept from it
    assert result["route"] == "direct"
    assert 0.6 < result["seconds"] / (len(TEXT) / speech.PACE["Kannada"]) < 1.6  # its words, not a babble or a cut
    assert capsys.readouterr().out == ""  # F5-TTS's notes went to the log: stdout carries the MCP messages
    other = reader_says(TEXT, "kn-IN-GaganNeural", kannada_voice / "gagan.mp3")  # another Kannada voice
    own = likeness(result["output_file"], voices.voice_file("Sapna"))
    assert own > 0.8 and own > likeness(result["output_file"], other) + 0.1, own
