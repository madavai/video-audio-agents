"""Speech in a saved voice, made on the computer by Chatterbox: speak (text or a transcript), speak_timed (dubbing:
every line at its own time) and change_voice (the same words and timing in another voice).
English, Hindi, French and Spanish are spoken directly in the voice. Kannada and Tamil are read by a free Microsoft
reader voice (online) first, then changed into the saved voice."""
import asyncio
import gc
import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from mcp.server.mcpserver.exceptions import ToolError

from . import clips, models, paths, voices
from .texts import SEGMENTS, existing, read_json

log = logging.getLogger("engine.speech")
LANGUAGES = ["English", "Kannada", "Hindi", "French", "Spanish", "Tamil"]
CLONED = {"English": "en", "Hindi": "hi", "French": "fr", "Spanish": "es"}
READERS = {"Kannada": ("kn-IN-GaganNeural", "kn-IN-SapnaNeural"), "Tamil": ("ta-IN-ValluvarNeural", "ta-IN-PallaviNeural")}
# The voice models talk a little faster than people do; the result is slowed without changing the pitch.
SPEEDS = {"little_slower": 0.9, "slower": 0.8, "as_made": 1.0}
FASTEST = 1.15  # dubbing: how much a line may be sped up to fit before the next one
PAUSE = 0.4  # seconds between sentences


def speak(job, voice: str, language: str, speed: str = "little_slower", text: str | None = None,
          transcript_file: str | None = None, output_name: str | None = None) -> dict:
    """Reads text, or a transcript or any text file (its "[12.5s]" times are left out), aloud in the voice.
    Saved next to the file, or in Documents/VideoAudioAgents/Speech/ for text."""
    check_language(language)
    if transcript_file:
        source = existing(transcript_file)
        words, folder, name = plain_text(source.read_text(encoding="utf-8")), source.parent, source.stem
    else:
        words, folder = plain_text(text or ""), paths.output_root() / "Speech"
        # Named after its first words, so several readings can be told apart.
        name = paths.safe_name(" ".join(re.split(r"[.!?।]", words)[0].split()[:6]), "Speech", limit=40)
    if not words:
        raise ToolError("There are no words to read aloud. Give the text, or the path of a transcript.")
    with models.one_at_a_time(job), tempfile.TemporaryDirectory() as tmp:
        lines, rate = spoken(job.report, text_pieces(words), language, voices.sample(voice, tmp),
                             f"Speaking in the {in_voice(voice)}")
    gap = np.zeros(int(PAUSE * rate), np.float32)
    audio = np.concatenate([piece for line in lines for piece in (line, gap)])
    folder.mkdir(parents=True, exist_ok=True)
    output = paths.free_path(folder, f"{output_name or name} ({in_voice(voice)})", ".mp3")
    return {"output_file": str(output), "seconds": save_mp3(audio, rate, output, SPEEDS[speed])}


def speak_timed(job, segments_file: str, voice: str, language: str, speed: str = "little_slower") -> dict:
    """Dubbing: speaks each line of a (translated) .segments.json and puts it at the line's start time, so the new
    audio follows the video. A line too long for its time is sped up a little; what still doesn't fit is reported."""
    check_language(language)
    source = existing(segments_file)
    # Lines without a word (a translated "…" over music) stay silent.
    segments = read_json(source.read_text(encoding="utf-8"), segments=True)
    segments = [s for s in segments if re.search(r"\w", s["text"])]
    if not segments:
        raise ToolError(f"{source.name} has no lines to speak.")
    count, segments = len(segments), joined(segments)
    with models.one_at_a_time(job), tempfile.TemporaryDirectory() as tmp:
        lines, rate = spoken(part(job.report, 0, 95), [plain_text(s["text"]) for s in segments], language,
                             voices.sample(voice, tmp), f"Dubbing in the {in_voice(voice)}")
    timing, overruns = place(segments, [len(line) / rate for line in lines], SPEEDS[speed])
    job.report(95, "Putting each line at its time")
    lines = [tempo(line, rate, line_tempo) for line, (line_tempo, _) in zip(lines, timing)]
    track = np.zeros(max(round(at * rate) + len(line) for line, (_, at) in zip(lines, timing)), np.float32)
    for line, (_, at) in zip(lines, timing):
        track[round(at * rate):round(at * rate) + len(line)] += line
    base = source.name.removesuffix(SEGMENTS) if source.name.endswith(SEGMENTS) else source.stem
    output = paths.free_path(source.parent, f"{base} ({in_voice(voice)})", ".mp3")
    return {"output_file": str(output), "seconds": save_mp3(track, rate, output), "lines": count,
            "overruns": overruns[:20], "overrun_count": len(overruns)}


def change_voice(job, file: str, voice: str, speed: str = "as_made") -> dict:
    """The same words and timing as an audio or video file, in the saved voice. Silence stays silence."""
    source = existing(file)
    audio = voices.read_audio(source, 16000)
    with models.one_at_a_time(job), tempfile.TemporaryDirectory() as tmp:
        sample = voices.sample(voice, tmp)  # an unknown voice is reported before the model loads
        vc = load("voice", job.report)
        vc.set_target_voice(sample)
        audio = convert(vc, audio, 16000, tmp, job.report, f"Changing it into the {in_voice(voice)}")
    output = paths.free_path(source.parent, f"{source.stem} ({in_voice(voice)})", ".mp3")
    return {"output_file": str(output), "seconds": save_mp3(audio, vc.sr, output, SPEEDS[speed])}


def in_voice(voice: str) -> str:
    """"Anna" -> "Anna voice", and "My voice" stays "My voice": for file names and messages."""
    return voice if voice.lower().endswith("voice") else f"{voice} voice"


def check_language(language: str) -> None:
    if language not in LANGUAGES:
        raise ToolError(f"{language} can't be spoken yet. The languages are: {', '.join(LANGUAGES)}.")


def load(kind: str, report):
    """A voice model: "voice" (changes a voice), "english" or "multilingual" (speak text), downloaded first if
    needed. Whatever big model was in memory before is let go first: each takes several GB."""
    if kind not in models.loaded:
        models.ensure([kind], report)
        models.loaded.clear()
        gc.collect()
        report(0, "Loading the voice model")
        folder = models.folder(kind)
        if kind == "voice":
            from chatterbox.vc import ChatterboxVC
            models.loaded[kind] = ChatterboxVC.from_local(folder, "cpu")
        elif kind == "english":
            from chatterbox.tts import ChatterboxTTS
            models.loaded[kind] = ChatterboxTTS.from_local(folder, "cpu")
        else:
            from chatterbox.models.tokenizers import tokenizer
            # Only for Chinese, which isn't offered: it would fetch word lists from the internet on every first load.
            tokenizer.ChineseCangjieConverter = lambda model_dir=None: None
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            models.loaded[kind] = ChatterboxMultilingualTTS.from_local(folder, "cpu")
    return models.loaded[kind]


def spoken(report, texts: list, language: str, sample: str, label: str) -> tuple[list, int]:
    """Each text spoken in the voice of `sample`, as its own audio without the silence around it. Returns the
    pieces and their sample rate."""
    if language in CLONED:
        model = load("english" if language == "English" else "multilingual", report)
        model.prepare_conditionals(sample)
    else:
        reader, model = reader_for(language, sample), load("voice", report)
        model.set_target_voice(sample)
    lines, started = [], time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        for i, text in enumerate(texts):
            report(i / len(texts) * 100, f"{label}: {i + 1} of {len(texts)}{time_left(started, i, len(texts))}")
            if language == "English":
                audio = model.generate(text).squeeze(0).numpy()
            elif language in CLONED:
                audio = model.generate(text, language_id=CLONED[language]).squeeze(0).numpy()
            else:
                audio = convert(model, read_aloud(text, reader, tmp), 16000, tmp)
            lines.append(trimmed(audio, model.sr))
    report(100, f"{label}: done")
    return lines, model.sr


def convert(vc, audio: np.ndarray, rate: int, tmp, report=None, label: str = "") -> np.ndarray:
    """`audio` re-spoken in the voice set on `vc`, in pieces of at most 20 seconds cut at quiet moments. Each piece
    keeps its length, so the timing stays the same; pieces too short or too quiet to hold speech stay silent."""
    import soundfile
    cuts, pieces, started = cut_points(audio, rate), [], time.monotonic()
    count = len(cuts) - 1
    for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
        if report:
            report(i / count * 100, f"{label}: part {i + 1} of {count}{time_left(started, i, count)}")
        length = round((b - a) / rate * vc.sr)
        if b - a < 0.3 * rate or np.abs(audio[a:b]).max() < 0.01:
            pieces.append(np.zeros(length, np.float32))
            continue
        piece = Path(tmp) / "piece.wav"
        soundfile.write(piece, audio[a:b], rate)
        new = vc.generate(str(piece)).squeeze(0).numpy()
        pieces.append(np.pad(new, (0, max(0, length - len(new))))[:length])
    if report:
        report(100, f"{label}: done")
    return np.concatenate(pieces)


def reader_for(language: str, sample: str) -> str:
    """The male or female reader voice, whichever is closer to the pitch of the saved voice."""
    import librosa
    audio, rate = librosa.load(sample, sr=16000)
    pitch = float(np.median(librosa.yin(audio, fmin=60, fmax=400, sr=rate)))
    male, female = READERS[language]
    return male if pitch < 165 else female


def read_aloud(text: str, reader: str, tmp) -> np.ndarray:
    """The text read by a Microsoft reader voice (needs the internet), as 16 kHz samples."""
    import edge_tts
    path = Path(tmp) / "reader.mp3"
    try:
        asyncio.run(edge_tts.Communicate(text, reader).save(str(path)))
    except edge_tts.exceptions.NoAudioReceived:  # nothing speakable in it, e.g. only punctuation
        return np.zeros(0, np.float32)
    except Exception as e:
        log.warning("The reader voice failed: %s", e)
        raise ToolError("Kannada and Tamil are read by an online reader voice first, and it couldn't be reached. "
                        "Check the internet connection and try again.") from e
    return voices.read_audio(path, 16000)


def trimmed(audio: np.ndarray, rate: int) -> np.ndarray:
    """Without the silence or faint noise the voice models often leave before and after the words (a little is kept,
    so soft endings aren't cut)."""
    import librosa
    loud = librosa.effects.split(audio, top_db=25) if audio.size else []
    if not len(loud):
        return audio
    return audio[max(0, loud[0][0] - int(0.05 * rate)):loud[-1][1] + int(0.15 * rate)]


def joined(segments: list, shortest: int = 40, gap: float = 1.5) -> list:
    """Dubbing: a short line is spoken together with the next one when that follows within `gap` seconds, starting at
    the first one's time. On their own, short lines come out garbled: babble after the words, long silences, or a lost
    last word (measured on Hindi); whole sentences don't."""
    lines = []
    for segment in segments:
        last = lines[-1] if lines else None
        if last and len(last["text"]) < shortest and segment["start"] - last["end"] < gap:
            lines[-1] = {**last, "end": segment["end"], "text": f"{last['text']} {segment['text']}"}
        else:
            lines.append(dict(segment))
    return lines


def place(segments: list, lengths: list, speed: float) -> tuple[list, list]:
    """Dubbing: (tempo, start in seconds) for each spoken line. A line starts at its own time (or right after the
    line before, if that one ran long) and plays at `speed`; if that doesn't fit before the next line starts, it is
    sped up, at most to 1.15 times. Lines that still don't fit are returned as overruns."""
    timing, overruns, free_from = [], [], 0.0
    for i, (segment, length) in enumerate(zip(segments, lengths)):
        at = max(float(segment["start"]), free_from)
        until = float(segments[i + 1]["start"]) if i + 1 < len(segments) else float(segment["end"])
        line_tempo = min(max(speed, length / (until - at)), FASTEST) if until > at else FASTEST
        free_from = at + length / line_tempo
        if free_from > until + 0.05:
            overruns.append({"at": clips.clock(float(segment["start"])), "over_by": round(free_from - until, 1)})
        timing.append((line_tempo, at))
    return timing, overruns


def plain_text(text: str) -> str:
    """The words to read aloud: without "[12.5s]" times, markdown marks (#, *, bullets) or line breaks."""
    stamped = re.findall(r"(?m)^\s*\[\d+(?:\.\d+)?s\]\s*(.*)$", text)
    if stamped:
        return " ".join(line.strip() for line in stamped if line.strip())
    lines = [re.sub(r"[*_`#]+", "", re.sub(r"^\s*(#+|[-*>])\s+", "", line)).strip() for line in text.splitlines()]
    # A heading or bullet without a full stop still gets the pause of one.
    return " ".join(line if line.endswith((".", "!", "?", "।", ":", ";", ",")) else line + "."
                    for line in lines if line)


def text_pieces(text: str, limit: int = 300) -> list:
    """Sentence-sized pieces of at most about `limit` characters (the voice models speak one piece at a time)."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?।])\s+", text.strip()):
        while len(sentence) > limit:  # a very long sentence: split it at a space
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    return [p for p in pieces + [current] if p]


def cut_points(audio: np.ndarray, rate: int, limit: float = 20) -> list:
    """Where to cut long audio into pieces of at most `limit` seconds, preferring quiet moments."""
    import librosa
    longest, hop = int(limit * rate), 512
    if len(audio) <= longest:
        return [0, len(audio)]
    loud = librosa.effects.split(audio, top_db=35)
    quiet = [(a[1] + b[0]) // 2 for a, b in zip(loud, loud[1:])]
    volume = librosa.feature.rms(y=audio, hop_length=hop)[0]
    cuts, last = [0], 0
    while len(audio) - last > longest:
        options = [q for q in quiet if last < q <= last + longest]
        if options:
            last = int(options[-1])
        else:  # no pause found: cut at the quietest moment in the second half of the window
            low, high = (last + longest // 2) // hop, (last + longest) // hop
            last = (low + int(volume[low:high].argmin())) * hop
        cuts.append(last)
    return cuts + [len(audio)]


def time_left(started: float, done: int, total: int) -> str:
    """", about 12 minutes left", estimated from the pieces done so far."""
    if not done:
        return ""
    minutes = (time.monotonic() - started) / done * (total - done) / 60
    return ", less than a minute left" if minutes < 1 else f", about {round(minutes)} minutes left"


def part(report, low: float, high: float):
    """A progress report for one step of a job: its 0-100% shows as low-high% of the whole job."""
    return lambda percent, message: report(low + percent / 100 * (high - low), message)


def tempo(audio: np.ndarray, rate: int, factor: float) -> np.ndarray:
    """Faster (factor above 1) or slower without changing the pitch: ffmpeg's atempo."""
    if abs(factor - 1.0) < 0.001 or not audio.size:
        return audio
    raw = ffmpeg(["-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-", "-filter:a", f"atempo={factor:.4f}",
                  "-f", "f32le", "-"], audio)
    return np.frombuffer(raw, dtype=np.float32)


def save_mp3(audio: np.ndarray, rate: int, output: Path, speed: float = 1.0) -> float:
    """Saves the audio as an .mp3 at this speed. Returns its length in seconds. A failed save leaves no file."""
    audio = tempo(audio, rate, speed)
    try:
        ffmpeg(["-f", "f32le", "-ar", str(rate), "-ac", "1", "-i", "-", "-c:a", "libmp3lame", "-q:a", "2", "-n",
                str(output)], audio)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return round(len(audio) / rate, 1)


def ffmpeg(args: list, audio: np.ndarray) -> bytes:
    """Runs ffmpeg with the samples piped in; returns what it writes out."""
    exe = str(models.ensure_ffmpeg() / f"ffmpeg{clips.EXE}")
    result = subprocess.run([exe, "-hide_banner", "-loglevel", "error", *args], input=audio.astype(np.float32).tobytes(),
                            capture_output=True, creationflags=clips.NO_WINDOW)
    if result.returncode != 0:
        errors = result.stderr.decode(errors="replace").strip()
        log.error("ffmpeg failed: %s\n%s", args, errors)
        raise ToolError(f"Saving the speech failed ({errors.splitlines()[-1] if errors else 'ffmpeg stopped'}).")
    return result.stdout
