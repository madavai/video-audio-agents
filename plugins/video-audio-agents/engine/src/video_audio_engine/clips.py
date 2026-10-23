"""cut_clip and merge_audio_video: ffmpeg edits with progress (a dub's music is kept by music.py). On Stop or
failure ffmpeg is stopped and the half-made file removed."""
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import models, paths, subtitles
from .texts import existing

log = logging.getLogger("engine.clips")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console window flashing up on Windows
EXE = ".exe" if sys.platform == "win32" else ""


def cut_clip(job, video_file: str, start: str, end: str, subtitle_file: str | None = None) -> dict:
    source = existing(video_file)
    first, last = seconds(start), seconds(end)
    length = probe_seconds(source)
    last = min(last, length)
    if first >= length:
        raise ToolError(f"The clip starts at {clock(first)}, but {source.name} is only {clock(length)} long.")
    if last <= first:
        raise ToolError("The end time must be after the start time.")
    name = f"{source.stem} (clip {clock(first, '-')} to {clock(last, '-')})"
    if not subtitle_file:  # copied as it is: instant, but the start snaps to the nearest keyframe before it
        output = paths.free_path(source.parent, name, source.suffix)
        # Picture and sound only: a timecode or data track (common in professional exports) can't be copied into an mp4.
        run(job, ["-ss", f"{first:.3f}", "-i", str(source), "-t", f"{last - first:.3f}", "-map", "0:v?", "-map", "0:a?",
                  "-c", "copy", "-avoid_negative_ts", "make_zero"], output, last - first, "Cutting the clip")
        return {"clip_file": str(output)}
    if not has_video(source):
        raise ToolError("Captions can only be burned into a video, and this file has no picture.")
    cues = subtitles.window(subtitles.read(existing(subtitle_file)), first, last)
    output = paths.free_path(source.parent, name + " (captions)", ".mp4")
    with tempfile.TemporaryDirectory() as tmp:  # captions shifted to the clip, under a plain name for the filter
        (Path(tmp) / "captions.srt").write_text(subtitles.write(cues, "srt"), encoding="utf-8")
        run(job, ["-ss", f"{first:.3f}", "-i", str(source), "-t", f"{last - first:.3f}",
                  "-vf", "subtitles=captions.srt:force_style='Fontsize=20,Outline=1.5,MarginV=24'",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart"],
            output, last - first, "Making the clip with captions", cwd=tmp)
    return {"clip_file": str(output)}


def merge_audio_video(job, video_file: str, audio_file: str, segments_file: str | None = None) -> dict:
    """Replaces the video's sound with the audio file: silence added if the audio is shorter, cut if longer.
    For a dub, segments_file holds its lines: the video's own sound is kept wherever nobody speaks, and its music
    and sound effects play on under the dub."""
    video, audio = existing(video_file), existing(audio_file)
    if not has_video(video):
        raise ToolError(f"{video.name} has no picture to put the audio under.")
    length = probe_seconds(video)
    # "Lesson (Hindi).mp3" under "Lesson.mp4" becomes "Lesson (Hindi).mp4".
    name = audio.stem if audio.stem.startswith(video.stem) and audio.stem != video.stem else f"{video.stem} (new audio)"
    output = paths.free_path(video.parent, name, ".mp4")
    start = 0  # where the progress of putting it under the video starts
    with tempfile.TemporaryDirectory() as tmp:
        if segments_file and has_audio(video):
            from . import music  # loads PyTorch: only for dubs
            sound, start = Path(tmp) / "sound.wav", 90
            with models.one_at_a_time(job):
                music.under_dub(lambda pct, message: job.report(pct * 0.9, message), video, audio,
                                existing(segments_file), sound)
            audio = sound
        run(job, ["-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                  "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.3f}", "-movflags", "+faststart"],
            output, length, "Putting the new audio under the video", start=start)
    return {"output_file": str(output)}


def run(job, args: list, output: Path, seconds_long: float, label: str, cwd=None, start: float = 0) -> None:
    """Runs ffmpeg, reporting progress (from `start`%, when an earlier step of the job came first). On Stop or
    failure: stops ffmpeg and removes the half-made output."""
    ffmpeg = str(models.ensure_ffmpeg() / f"ffmpeg{EXE}")
    command = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-progress", "pipe:1", *args, "-n", str(output)]
    job.report(start, label)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd,
                               creationflags=NO_WINDOW)
    try:
        for line in process.stdout:
            if line.startswith("out_time_us=") and line.strip()[12:].isdigit():
                pct = min(99.0, int(line.strip()[12:]) / 1e6 / max(seconds_long, 0.1) * 100)
                job.report(start + pct * (100 - start) / 100, f"{label}... {int(pct)}%")
        errors = process.stderr.read()
        process.wait()
    except BaseException:  # Stop (or anything else): end ffmpeg now
        process.kill()
        process.wait()
        output.unlink(missing_ok=True)
        raise
    if process.returncode != 0:
        output.unlink(missing_ok=True)
        log.error("ffmpeg failed: %s\n%s", command, errors)
        raise ToolError(f"{label} failed ({errors.strip().splitlines()[-1] if errors.strip() else 'ffmpeg stopped'}).")
    job.report(100, f"{label}: done")


def probe(file: Path, *args) -> str:
    ffprobe = str(models.ensure_ffmpeg() / f"ffprobe{EXE}")
    result = subprocess.run([ffprobe, "-v", "error", *args, "-of", "csv=p=0", str(file)], capture_output=True,
                            text=True, creationflags=NO_WINDOW)
    return result.stdout.strip()


def probe_seconds(file: Path) -> float:
    try:
        return float(probe(file, "-show_entries", "format=duration").splitlines()[0])
    except (ValueError, IndexError):
        raise ToolError(f"{file.name} couldn't be read as audio or video.") from None


def has_video(file: Path) -> bool:
    return "video" in probe(file, "-select_streams", "v", "-show_entries", "stream=codec_type")


def has_audio(file: Path) -> bool:
    return "audio" in probe(file, "-select_streams", "a", "-show_entries", "stream=codec_type")


def seconds(value) -> float:
    """"90", "90.5", "1:30", "01:30", "1:02:03" or a number → seconds."""
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return float(text)
    if re.fullmatch(r"\d+(:\d{1,2}){1,2}(\.\d+)?", text):
        total = 0.0
        for part in text.split(":"):
            total = total * 60 + float(part)
        return total
    raise ToolError(f'"{value}" isn\'t a time. Use minutes:seconds like 01:30, or seconds like 90.')


def clock(value: float, separator: str = ":") -> str:
    """90 → "1:30"; 3723 → "1:02:03"."""
    total = int(value)
    h, m, s = total // 3600, total // 60 % 60, total % 60
    return f"{h}{separator}{m:02}{separator}{s:02}" if h else f"{m}{separator}{s:02}"
