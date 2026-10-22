"""transcribe: speech to text with faster-whisper. Writes a .txt (with timestamps, or as paragraphs) and a
.segments.json (start, end, text per line) that subtitles, clips and dubbing are made from."""
import gc
import json
from pathlib import Path

import av
from mcp.server.mcpserver.exceptions import ToolError

from . import models, paths

ACCURACY = {"fast": "base", "balanced": "small", "accurate": "large-v3-turbo"}
AUDIO = {".mp3", ".m4a", ".wav", ".webm", ".ogg", ".opus", ".flac", ".aac"}  # delete_audio_after never deletes a video


def load(name: str, job):
    """The speech model, downloaded first if needed. Batched and with silence skipped: much faster on a CPU."""
    if name not in models.loaded:
        models.ensure([name], job.report)
        job.report(0, "Loading the speech-to-text model")
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        models.loaded.clear()  # a voice model takes several GB: let it go first
        gc.collect()
        # 4 threads: more crashed outright (Windows stack overflow) with full batches of 8 on long recordings,
        # e.g. 12 threads on a 24-core PC; 4 was as fast in measurements.
        model = WhisperModel(str(models.folder(name)), device="cpu", compute_type="int8", cpu_threads=4)
        models.loaded[name] = BatchedInferencePipeline(model)
    return models.loaded[name]


def transcribe(job, file: str, accuracy: str = "balanced", timestamps: bool = True,
               delete_audio_after: bool = False) -> dict:
    source = Path(file)
    if not source.is_file():
        raise ToolError(f"There is no file at {source}.")
    with models.one_at_a_time(job):
        pipeline = load(ACCURACY[accuracy], job)
        job.report(0, "Listening")
        try:
            # Word timings instead of segment timings: the batched segment timings drop words at chunk ends.
            segments, info = pipeline.transcribe(str(source), batch_size=8, word_timestamps=True)
            lines = to_lines(segments, info.duration, job)
        except av.error.FFmpegError as e:
            raise ToolError(f"{source.name} couldn't be read as audio or video.") from e

    # Written only now, all at once, so a stopped transcript leaves no half-written files.
    name = paths.free_name(source.parent, source.stem, [".txt", ".segments.json"])
    transcript, segments_file = source.parent / f"{name}.txt", source.parent / f"{name}.segments.json"
    transcript.write_text(as_text(lines, timestamps), encoding="utf-8")
    segments_file.write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
    if delete_audio_after and source.suffix.lower() in AUDIO:
        source.unlink()
    job.report(100, "Transcript ready")
    return {"transcript_file": str(transcript), "segments_file": str(segments_file), "language": info.language,
            "lines": len(lines), "duration_seconds": round(info.duration, 1)}


def to_lines(segments, duration: float, job) -> list:
    """Sentence-sized lines from the word timings: a new line after a sentence ends, at a pause of over a second (a sentence must last a second, so "Okay." joins the next one),
    or when a line would run past 12 seconds."""
    lines, words = [], []

    def finish_line():
        text = "".join(w.word for w in words).strip()
        if text:
            lines.append({"start": round(words[0].start, 2), "end": round(words[-1].end, 2), "text": text})
        words.clear()

    for segment in segments:
        for word in segment.words or []:
            if words and (word.start - words[-1].end > 1.0 or word.end - words[0].start > 12):
                finish_line()
            words.append(word)
            if word.word.strip().endswith((".", "?", "!", "।", "。")) and word.end - words[0].start > 1.0:
                finish_line()
        pct = min(99.0, segment.end / max(duration, 0.1) * 100)
        job.report(pct, f"Transcribing... {int(pct)}%")
    finish_line()
    return lines


def as_text(lines: list, timestamps: bool) -> str:
    """One "[12.5s] text" line per segment, or flowing paragraphs of about 400 characters."""
    if timestamps:
        return "".join(f"[{line['start']:.1f}s] {line['text']}\n" for line in lines)
    paragraphs, current = [], ""
    for line in lines:  # a new paragraph after a sentence once the current one gets long
        current = f"{current} {line['text']}".strip()
        if len(current) > 400 and current.endswith((".", "?", "!", "。", "।")):
            paragraphs.append(current)
            current = ""
    return "\n\n".join(paragraphs + [current] if current else paragraphs) + "\n"
