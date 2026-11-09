"""Saved voices: up to 30 seconds of a person's speech as Documents/VideoAudioAgents/voices/<name>.wav, saved only
with their permission (uploaded or recorded). The voice models listen to 10 seconds, so each job uses the clearest
10 seconds of the saved voice.
For Kannada in the voice itself (indic.py), a voice also keeps the person's reading of SENTENCE as
<name>.kannada.flac: IndicF5 needs the exact words said in what it listens to."""
import logging
import subprocess
import sys
from pathlib import Path

import numpy as np
from mcp.server.mcpserver.exceptions import ToolError

from . import models, paths
from .clips import EXE, NO_WINDOW
from .texts import existing

log = logging.getLogger("engine.voices")
RATE = 24000  # the voice models' own sample rate
LONGEST, SHORTEST = 30, 10  # seconds of speech kept, and needed
# Where the person allows the microphone: on a Mac, for the app Claude runs in (Terminal or the Claude app).
MICROPHONE = ("System Settings, Privacy & Security, Microphone" if sys.platform == "darwin"
              else "Windows Settings, Privacy, Microphone")
CONSENT = ("A voice is only saved when it is the person's own, or they agreed to it being used. "
           "Ask them first, then try again with consent.")
# Read aloud once by the person, for Kannada in their voice: "Hello! This is my voice. The weather is lovely today, so
# let's go to the park this evening and walk for a while." About 6 to 9 seconds at a normal pace.
SENTENCE = "ನಮಸ್ಕಾರ! ಇದು ನನ್ನ ಧ್ವನಿ. ಇಂದು ಹವಾಮಾನ ತುಂಬಾ ಚೆನ್ನಾಗಿದೆ, ಆದ್ದರಿಂದ ಸಂಜೆ ಉದ್ಯಾನವನಕ್ಕೆ ಹೋಗಿ ಸ್ವಲ್ಪ ಹೊತ್ತು ನಡೆಯೋಣ."
READING = ".kannada.flac"  # beside the voice's .wav (a .flac, so it isn't listed as a voice of its own)


def voices_dir() -> Path:
    folder = paths.output_root() / "voices"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def list_voices() -> dict:
    names = sorted(path.stem for path in voices_dir().glob("*.wav"))
    return {"voices": names, "folder": str(voices_dir()), "kannada_sentence": SENTENCE,
            "kannada_readings": [name for name in names if (voices_dir() / f"{name}{READING}").is_file()]}


def kannada_reading(voice: str) -> Path | None:
    """The voice's reading of SENTENCE, if the person has read it."""
    path = voice_file(voice).with_name(f"{voice}{READING}")
    return path if path.is_file() else None


def voice_file(voice: str) -> Path:
    path = voices_dir() / f"{voice}.wav"
    if not path.is_file():
        names = list_voices()["voices"]
        saved = f"The saved voices are: {', '.join(names)}." if names else "Save one first (upload or record)."
        raise ToolError(f'There is no saved voice called "{voice}". {saved}')
    return path


def save_voice(job, source_file: str, name: str, consent: bool, kannada_sentence: bool = False) -> dict:
    """A voice from any audio or video file: the clearest 30 seconds of its first 10 minutes. With
    kannada_sentence: the file is the person reading SENTENCE, kept with their saved voice `name`."""
    if not consent:
        raise ToolError(CONSENT)
    source = existing(source_file)
    job.report(0, "Reading the recording")
    if kannada_sentence:
        voice_file(name)  # an unknown voice is reported before anything is read
        return keep_reading(read_audio(source, RATE, seconds=60), name)
    return keep(read_audio(source, RATE, seconds=600), name)


def record_voice(job, name: str, seconds: int, consent: bool, kannada_sentence: bool = False) -> dict:
    """Records the computer's default microphone: it waits (up to a minute) for the person to start speaking, then
    records 10 to 30 seconds, so no words are lost while the request reaches the engine. Esc saves nothing.
    With kannada_sentence: the person reads SENTENCE for their saved voice `name`; it stops 2 seconds after they
    stop speaking (at most 20 seconds)."""
    if not consent:
        raise ToolError(CONSENT)
    if kannada_sentence:
        voice_file(name)
    import sounddevice
    seconds, step = (20 if kannada_sentence else min(max(int(seconds), SHORTEST), LONGEST)), RATE // 5
    chunks, waited = [], 0
    try:
        with sounddevice.InputStream(samplerate=RATE, channels=1, dtype="float32") as microphone:
            while len(chunks) * step < seconds * RATE:
                chunk = microphone.read(step)[0][:, 0]
                if not chunks and np.abs(chunk).max() < 0.02:  # not speaking yet
                    waited += step
                    if waited > 60 * RATE:
                        raise ToolError("Nothing was heard for a minute. Check the microphone is switched on and "
                                        f"allowed ({MICROPHONE}), then try again.")
                    job.report(0, "Listening: start speaking whenever you are ready")
                    continue
                chunks.append(chunk)
                if kannada_sentence and len(chunks) > 15 and max(np.abs(c).max() for c in chunks[-10:]) < 0.02:
                    break  # 2 seconds of quiet after the reading
                left = seconds - len(chunks) * step / RATE
                job.report(100 - left / seconds * 100, f"Recording ({left:.0f} seconds left)")
    except sounddevice.PortAudioError as e:  # no microphone, or it is in use
        log.warning("Recording failed: %s", e)
        raise ToolError("The microphone couldn't be used. Check one is connected and not in use, then try again.") from e
    return keep_reading(np.concatenate(chunks), name) if kannada_sentence else keep(np.concatenate(chunks), name)


def keep(audio: np.ndarray, name: str) -> dict:
    """Saves the speech without the silence around it, at most 30 seconds, under a name not used yet."""
    import librosa
    import soundfile
    if audio.size == 0 or np.abs(audio).max() < 0.01:
        raise ToolError("There is no sound in that recording. If it was recorded here, check the microphone is "
                        f"switched on and allowed ({MICROPHONE}).")
    audio = librosa.effects.trim(audio, top_db=35)[0]
    if len(audio) < SHORTEST * RATE:
        raise ToolError(f"That is only {len(audio) / RATE:.0f} seconds of speaking; a voice needs at least "
                        f"{SHORTEST}. Use 20 to 30 seconds of natural speech.")
    audio = best_window(audio, RATE, LONGEST)
    path = paths.free_path(voices_dir(), name.strip() or "My voice", ".wav")
    soundfile.write(path, audio, RATE)
    return {"voice": path.stem, "sample_file": str(path), "seconds": round(len(audio) / RATE, 1)}


def keep_reading(audio: np.ndarray, voice: str) -> dict:
    """The person's reading of SENTENCE, without the silence around it, as <voice>.kannada.flac. A new reading
    replaces the old one (the person read it again), like the voice's pronunciation list."""
    import librosa
    import soundfile
    if audio.size == 0 or np.abs(audio).max() < 0.01:
        raise ToolError("There is no sound in that recording. If it was recorded here, check the microphone is "
                        f"switched on and allowed ({MICROPHONE}).")
    audio = librosa.effects.trim(audio, top_db=35)[0]
    seconds = len(audio) / RATE
    if not 3 <= seconds <= 15:
        raise ToolError(f"That reading is {seconds:.0f} seconds long, and the sentence takes about 6 to 9 seconds. "
                        "Read just the sentence once, at a normal pace.")
    path = voice_file(voice).with_name(f"{voice}{READING}")
    part = path.with_name(path.name + ".part")
    soundfile.write(part, audio, RATE, format="FLAC")
    part.replace(path)
    return {"voice": voice, "kannada_reading": str(path), "seconds": round(seconds, 1)}


def sample(voice: str, folder) -> str:
    """The clearest 10 seconds of a saved voice at an even volume, as voice-sample.wav in `folder`."""
    import soundfile
    audio = best_window(read_audio(voice_file(voice), RATE), RATE, 10)
    path = Path(folder) / "voice-sample.wav"
    soundfile.write(path, audio / (float(np.abs(audio).max()) or 1.0) * 0.9, RATE)
    return str(path)


def best_window(audio: np.ndarray, rate: int, seconds: float) -> np.ndarray:
    """The `seconds` with the most speech in them: a window slid over the loudness, so a quiet start is skipped."""
    import librosa
    window, hop = int(seconds * rate), 512
    if len(audio) <= window:
        return audio
    volume = librosa.feature.rms(y=audio, hop_length=hop)[0]
    start = int(np.convolve(volume, np.ones(window // hop), "valid").argmax()) * hop
    return audio[start:start + window]


def read_audio(file, rate: int, seconds: float | None = None, channels: int = 1) -> np.ndarray:
    """Any audio or video file as mono samples at `rate` (at most its first `seconds`), decoded by ffmpeg.
    With channels=2: stereo, as rows of [left, right]."""
    ffmpeg = str(models.ensure_ffmpeg() / f"ffmpeg{EXE}")
    limit = ["-t", str(seconds)] if seconds else []
    result = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-i", str(file), *limit, "-vn",
                             "-ac", str(channels), "-ar", str(rate), "-f", "f32le", "-"], capture_output=True,
                            creationflags=NO_WINDOW)
    if result.returncode != 0 or not result.stdout:
        log.error("ffmpeg couldn't read %s: %s", file, result.stderr.decode(errors="replace"))
        raise ToolError(f"{Path(file).name} couldn't be read as audio.")
    audio = np.frombuffer(result.stdout, dtype=np.float32).copy()
    return audio.reshape(-1, channels) if channels > 1 else audio
