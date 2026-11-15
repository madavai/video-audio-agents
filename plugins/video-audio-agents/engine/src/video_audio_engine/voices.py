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
QUIET, PAUSE = 5, 1.0  # seconds of quiet that end a reading of SENTENCE (record_voice), and its longest pause kept
# reading_fault: how alike what speech recognition hears in a reading and SENTENCE must be, and the share of the
# letters of its last two words it must hear there
HEARD, ENDING = 0.7, 0.5
FAULTS = {  # what is wrong with a reading that isn't the whole sentence (reading_fault), to finish a plain sentence
    "part": "stops before the end of the Kannada sentence",
    "other": "doesn't sound like the Kannada sentence (speech recognition heard other words)"}
heard = {}  # recordings already listened to, by their sound: what is wrong with each, if anything (once per session)


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
        return keep_reading(job, read_audio(source, RATE, seconds=60), name)
    return keep(read_audio(source, RATE, seconds=600), name)


def record_voice(job, name: str, seconds: int, consent: bool, kannada_sentence: bool = False) -> dict:
    """Records the computer's default microphone: it waits (up to a minute) for the person to start speaking, then
    records 10 to 30 seconds, so no words are lost while the request reaches the engine. The 0.6 seconds before the
    first sound are kept too, so a soft first syllable isn't cut. Esc saves nothing.
    With kannada_sentence: the person reads SENTENCE for their saved voice `name`; it stops once they have been
    quiet for QUIET seconds (at most 40 seconds), so pausing to look at the next words doesn't end it. A 2-second
    wait ended a reading at its comma, and the half reading made IndicF5 say the missing words before every text."""
    if not consent:
        raise ToolError(CONSENT)
    if kannada_sentence:
        voice_file(name)
    import sounddevice
    seconds, step = (40 if kannada_sentence else min(max(int(seconds), SHORTEST), LONGEST)), RATE // 5
    lead, chunks, waited, quiet = [], [], 0, QUIET * 5  # quiet: in chunks of 0.2 s
    try:
        with sounddevice.InputStream(samplerate=RATE, channels=1, dtype="float32") as microphone:
            while len(chunks) * step < seconds * RATE:
                chunk = microphone.read(step)[0][:, 0]
                if not chunks and np.abs(chunk).max() < 0.02:  # not speaking yet
                    lead = [*lead[-2:], chunk]
                    waited += step
                    if waited > 60 * RATE:
                        raise ToolError("Nothing was heard for a minute. Check the microphone is switched on and "
                                        f"allowed ({MICROPHONE}), then try again.")
                    job.report(0, "Listening: start speaking whenever you are ready")
                    continue
                chunks.append(chunk)
                if kannada_sentence and len(chunks) > quiet and max(np.abs(c).max() for c in chunks[-quiet:]) < 0.02:
                    break  # QUIET seconds of quiet after the reading
                left = seconds - len(chunks) * step / RATE
                job.report(100 - left / seconds * 100, f"Recording ({left:.0f} seconds left)")
    except sounddevice.PortAudioError as e:  # no microphone, or it is in use
        log.warning("Recording failed: %s", e)
        raise ToolError("The microphone couldn't be used. Check one is connected and not in use, then try again.") from e
    audio = np.concatenate(lead + chunks)
    return keep_reading(job, audio, name) if kannada_sentence else keep(audio, name)


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


def keep_reading(job, audio: np.ndarray, voice: str) -> dict:
    """The person's reading of SENTENCE, without the silence around it and with its pauses cut to PAUSE seconds, as
    <voice>.kannada.flac, once speech recognition heard the whole sentence in it. A new reading replaces the old one
    (the person read it again), like the voice's pronunciation list."""
    import librosa
    import soundfile
    if audio.size == 0 or np.abs(audio).max() < 0.01:
        raise ToolError("There is no sound in that recording. If it was recorded here, check the microphone is "
                        f"switched on and allowed ({MICROPHONE}).")
    audio = shorter_pauses(librosa.effects.trim(audio, top_db=35)[0])
    seconds = len(audio) / RATE
    if not 3 <= seconds <= 15:
        raise ToolError(f"That reading is {seconds:.0f} seconds long, and the sentence takes about 6 to 9 seconds. "
                        "Read just the sentence once, at a normal pace.")
    with models.one_at_a_time(job):
        fault = reading_fault(audio, job.report)
    if fault:
        raise ToolError(f"That recording {FAULTS[fault]}, so it wasn't kept. " + (
            "Read the whole sentence again: pauses are fine." if fault == "part" else
            "Read just the sentence once, in Kannada, with nothing else said while it records."))
    path = voice_file(voice).with_name(f"{voice}{READING}")
    part = path.with_name(path.name + ".part")
    soundfile.write(part, audio, RATE, format="FLAC")
    part.replace(path)
    return {"voice": voice, "kannada_reading": str(path), "seconds": round(seconds, 1)}


def shorter_pauses(audio: np.ndarray) -> np.ndarray:
    """The recording with the middle of each pause longer than PAUSE seconds taken out. People reading an unfamiliar
    sentence stop to look at the next words, and IndicF5 takes its pace from the reading: one 3-second pause made
    every take about 17% slower, and a few would have made a reading too long to keep."""
    import librosa
    keep, edge = np.ones(len(audio), bool), int(PAUSE * RATE / 2)
    sounds = librosa.effects.split(audio, top_db=35)
    for (_, end), (start, _) in zip(sounds, sounds[1:]):
        if start - end > 2 * edge:
            keep[end + edge:start - edge] = False
    return audio[keep]


def reading_fault(audio: np.ndarray, report) -> str | None:
    """None when a recording (samples at RATE) is a whole reading of SENTENCE, else what is wrong with it (a key of
    FAULTS). The accurate speech-to-text model listens with the language set to Kannada; what it hears must be at least
    HEARD alike to the sentence, letter by letter (difflib's ratio of the Kannada letters), with at least ENDING of the
    letters of the sentence's last two words heard in their place. IndicF5 is told the reading says SENTENCE, and says
    the words missing from it before every text: the second half of a reading that stopped at its comma (1.5.1), or
    the sentence's last words for a recording of other words (English talk while the microphone listened, 1.5.0).
    "part" is a recording at least half alike without the ending: a reading that stopped early.
    Measured with reader voices: whole readings 0.92 to 0.97 alike, ending 0.75 to 0.92 (with a 3-second pause too);
    stopped at the comma (with or without its first syllable) 0.54 to 0.63, the first 75% 0.63 to 0.74 and the first
    90% 0.82 to 0.87, all with ending 0; English speech 0. 24 FLEURS Kannada sentences by real speakers against
    their own words: 0.75 to 0.95 alike, ending 0.75 to 1. It listens in stretches of at most 10 seconds: in one
    stretch the model writes at most about 224 tokens (the sentence takes 174, more when heard badly), and in the
    usual 30-second stretches that cut the end off 9 of those 24 sentences.
    Only the accurate model writes Kannada (the fast and balanced ones heard none of it), and it runs on the processor
    here, so a graphics card that fails can't stop the Kannada voice. The caller holds models.one_at_a_time."""
    import difflib
    import hashlib
    import librosa
    from . import transcribe
    key = hashlib.sha1(audio.tobytes()).hexdigest()
    if key not in heard:
        pipeline, _ = transcribe.load("large-v3-turbo", report, device="cpu")
        report(0, "Listening to the Kannada reading")
        segments, _ = pipeline.transcribe(librosa.resample(audio, orig_sr=RATE, target_sr=16000), language="kn",
                                          chunk_length=10)
        said, meant, last = ([ch for ch in text if "\u0c80" <= ch <= "\u0cff"]  # the Kannada letters, nothing else
                             for text in ("".join(segment.text for segment in segments), SENTENCE,
                                          " ".join(SENTENCE.split()[-2:])))
        same = difflib.SequenceMatcher(None, said, meant, autojunk=False).get_matching_blocks()
        alike = 2 * sum(block.size for block in same) / (len(said) + len(meant))
        end = len(meant) - len(last)  # where the last two words start
        ending = sum(max(0, block.b + block.size - max(block.b, end)) for block in same) / len(last)
        heard[key] = (None if alike >= HEARD and ending >= ENDING else
                      "part" if alike >= 0.5 and ending < ENDING else "other")
        log.info("The Kannada reading: %.2f alike, %.2f of the ending heard (%s)", alike, ending, heard[key])
    return heard[key]


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
