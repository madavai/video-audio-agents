"""Saved voices: up to 30 seconds of a person's speech as Documents/VideoAudioAgents/voices/<name>.wav, saved only
with their permission (uploaded or recorded). The voice models listen to 10 seconds, so each job uses the clearest
10 seconds of the saved voice."""
import logging
import subprocess
from pathlib import Path

import numpy as np
from mcp.server.mcpserver.exceptions import ToolError

from . import models, paths
from .clips import EXE, NO_WINDOW
from .texts import existing

log = logging.getLogger("engine.voices")
RATE = 24000  # the voice models' own sample rate
LONGEST, SHORTEST = 30, 10  # seconds of speech kept, and needed
CONSENT = ("A voice is only saved when it is the person's own, or they agreed to it being used. "
           "Ask them first, then try again with consent.")


def voices_dir() -> Path:
    folder = paths.output_root() / "voices"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def list_voices() -> dict:
    return {"voices": sorted(path.stem for path in voices_dir().glob("*.wav")), "folder": str(voices_dir())}


def voice_file(voice: str) -> Path:
    path = voices_dir() / f"{voice}.wav"
    if not path.is_file():
        names = list_voices()["voices"]
        saved = f"The saved voices are: {', '.join(names)}." if names else "Save one first (upload or record)."
        raise ToolError(f'There is no saved voice called "{voice}". {saved}')
    return path


def save_voice(job, source_file: str, name: str, consent: bool) -> dict:
    """A voice from any audio or video file: the clearest 30 seconds of its first 10 minutes."""
    if not consent:
        raise ToolError(CONSENT)
    source = existing(source_file)
    job.report(0, "Reading the recording")
    return keep(read_audio(source, RATE, seconds=600), name)


def record_voice(job, name: str, seconds: int, consent: bool) -> dict:
    """Records the computer's default microphone: it waits (up to a minute) for the person to start speaking, then
    records 10 to 30 seconds, so no words are lost while the request reaches the engine. Esc saves nothing."""
    if not consent:
        raise ToolError(CONSENT)
    import sounddevice
    seconds, step = min(max(int(seconds), SHORTEST), LONGEST), RATE // 5
    chunks, waited = [], 0
    try:
        with sounddevice.InputStream(samplerate=RATE, channels=1, dtype="float32") as microphone:
            while len(chunks) * step < seconds * RATE:
                chunk = microphone.read(step)[0][:, 0]
                if not chunks and np.abs(chunk).max() < 0.02:  # not speaking yet
                    waited += step
                    if waited > 60 * RATE:
                        raise ToolError("Nothing was heard for a minute. Check the microphone is switched on and "
                                        "allowed (Windows Settings, Privacy, Microphone), then try again.")
                    job.report(0, "Listening: start speaking whenever you are ready")
                    continue
                chunks.append(chunk)
                left = seconds - len(chunks) * step / RATE
                job.report(100 - left / seconds * 100, f"Recording ({left:.0f} seconds left)")
    except sounddevice.PortAudioError as e:  # no microphone, or it is in use
        log.warning("Recording failed: %s", e)
        raise ToolError("The microphone couldn't be used. Check one is connected and not in use, then try again.") from e
    return keep(np.concatenate(chunks), name)


def keep(audio: np.ndarray, name: str) -> dict:
    """Saves the speech without the silence around it, at most 30 seconds, under a name not used yet."""
    import librosa
    import soundfile
    if audio.size == 0 or np.abs(audio).max() < 0.01:
        raise ToolError("There is no sound in that recording. If it was recorded here, check the microphone is "
                        "switched on and allowed (Windows Settings, Privacy, Microphone).")
    audio = librosa.effects.trim(audio, top_db=35)[0]
    if len(audio) < SHORTEST * RATE:
        raise ToolError(f"That is only {len(audio) / RATE:.0f} seconds of speaking; a voice needs at least "
                        f"{SHORTEST}. Use 20 to 30 seconds of natural speech.")
    audio = best_window(audio, RATE, LONGEST)
    path = paths.free_path(voices_dir(), name.strip() or "My voice", ".wav")
    soundfile.write(path, audio, RATE)
    return {"voice": path.stem, "sample_file": str(path), "seconds": round(len(audio) / RATE, 1)}


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
