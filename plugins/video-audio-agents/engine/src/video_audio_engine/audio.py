"""clean_audio: brings a recording to -16 LUFS, the loudness podcast apps and YouTube expect for speech, and cuts
the silence at its start and end. Two ffmpeg passes: the first measures, the second writes (a single pass misses
the loudness of short recordings by several LU)."""
import json
import re

from mcp.server.mcpserver.exceptions import ToolError

from . import paths
from .clips import has_audio, probe, probe_seconds, run
from .texts import existing

TARGET = "I=-16:TP=-1.5:LRA=11"  # -16 LUFS, peaks at most -1.5 dB
QUIET = "-45dB"  # quieter than this for half a second counts as silence
KEEP = 0.3  # seconds of the silence kept before the first sound and after the last


def clean_audio(job, file: str, loudness: bool = True, trim_silence: bool = True) -> dict:
    source = existing(file)
    if not (loudness or trim_silence):
        raise ToolError("Nothing to do: ask for the loudness, the silence trimmed, or both.")
    if not has_audio(source):
        raise ToolError(f"{source.name} has no sound to clean.")
    video = has_picture(source)
    length = probe_seconds(source)
    said = run(job, ["-i", str(source), "-map", "0:a:0", "-af",
                     f"silencedetect=noise={QUIET}:d=0.5,loudnorm={TARGET}:print_format=json"],
               None, length, "Listening to the sound", end=50)
    measured = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", said)[0])
    if measured["input_i"] == "-inf":
        raise ToolError(f"{source.name} is silent from start to end.")

    first, last = 0.0, length
    if trim_silence and not video:  # cutting a video's sound would put its picture out of step
        starts = [float(t) for t in re.findall(r"silence_start: (-?[\d.]+)", said)]
        ends = [float(t) for t in re.findall(r"silence_end: ([\d.]+)", said)]
        silences = list(zip(starts, ends + [length]))  # a silence running to the end may have no end printed
        if silences and silences[0][0] <= 0.05:
            first = max(0.0, silences[0][1] - KEEP)
        if silences and silences[-1][1] >= length - 0.05:
            last = min(length, silences[-1][0] + KEEP)
        if last - first < 0.5:
            raise ToolError(f"{source.name} is silent from start to end.")
        if not loudness and first == 0 and last == length:
            raise ToolError(f"There is no silence to cut at the start or end of {source.name}; nothing was changed.")

    filters = [f"atrim={first:.3f}:{last:.3f},asetpts=PTS-STARTPTS"] if first > 0 or last < length else []
    if loudness:
        filters.append(f"loudnorm={TARGET}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
                       f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
                       f"offset={measured['target_offset']}:linear=true")
    rate = probe(source, "-select_streams", "a:0", "-show_entries", "stream=sample_rate") or "48000"
    filters.append(f"aresample={rate}")  # loudnorm works at 192 kHz
    if video:  # the picture is copied as it is
        output = paths.free_path(source.parent, f"{source.stem} (clean audio)", ".mp4")
        args = ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart"]
    else:  # the same kind of file (an mp3 stays an mp3), without cover art
        output = paths.free_path(source.parent, f"{source.stem} (clean audio)", source.suffix.lower())
        args = ["-map", "0:a:0"]
    run(job, ["-i", str(source), *args, "-af", ",".join(filters), "-b:a", "192k"], output, last - first,
        "Writing the clean sound", start=50)
    return {"output_file": str(output), "seconds": round(last - first, 1),
            "silence_cut_seconds": round(length - (last - first), 1),
            "loudness_before": float(measured["input_i"])}


def has_picture(file) -> bool:
    """A video's picture; an mp3's cover art doesn't count."""
    return "video,0" in probe(file, "-select_streams", "v", "-show_entries",
                              "stream=codec_type:stream_disposition=attached_pic").splitlines()
