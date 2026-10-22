"""make_subtitles: .srt or .vtt from a segments file (the original or a translation), in the usual readable
shape: at most 2 lines of 42 characters, at most 6 seconds on screen. Also reads subtitle files back, for
burning captions into a clip."""
import math
import re
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import paths
from .texts import SEGMENTS, read_json

MAX_SECONDS = 6.0


def make_subtitles(segments_file: str, format: str = "srt", max_chars: int = 42) -> dict:
    source = Path(segments_file)
    if not source.is_file():
        raise ToolError(f"There is no file at {source}.")
    segments = read_json(source.read_text(encoding="utf-8"), segments=True)
    cues = to_cues(segments, max(20, max_chars))
    base = source.name.removesuffix(SEGMENTS) if source.name.endswith(SEGMENTS) else source.stem
    path = paths.free_path(source.parent, base, f".{format}")
    path.write_text(write(cues, format), encoding="utf-8")
    return {"subtitle_file": str(path), "cues": len(cues)}


def to_cues(segments: list, max_chars: int = 42) -> list:
    """[(start, end, [line, line])] with each cue's time shared out by its share of the segment's characters."""
    cues, last_end = [], 0.0
    for segment in segments:
        text = " ".join(segment["text"].split())
        if not text:
            continue
        start = max(float(segment["start"]), last_end)
        seconds = max(float(segment["end"]) - start, 0.1)
        pieces = max(math.ceil(len(text) / (2 * max_chars)), math.ceil(seconds / MAX_SECONDS))
        while True:  # more, shorter pieces until every one fits on two lines and in six seconds
            chunks = split_evenly(text, pieces)
            lines = [wrap(chunk, max_chars) for chunk in chunks]
            total = sum(len(chunk) for chunk in chunks)
            times = [seconds * len(chunk) / total for chunk in chunks]
            fits = all(len(cue) <= 2 and all(len(line) <= max_chars for line in cue) for cue in lines)
            if (fits and max(times) <= MAX_SECONDS + 0.01) or pieces > len(text):
                break
            pieces += 1
        for cue, duration in zip(lines, times):
            cues.append((round(start, 3), round(start + duration, 3), cue))
            start += duration
        last_end = start
    return cues


def split_evenly(text: str, pieces: int) -> list:
    """Splits text at spaces into about `pieces` parts of similar length (a word longer than a part is cut)."""
    words, target = [], math.ceil(len(text) / pieces)
    for word in text.split(" "):
        while len(word) > target:  # a very long word, or a language written without spaces
            words.append(word[:target])
            word = word[target:]
        words.append(word)
    chunks, current = [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > target:
            chunks.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    return chunks + [current] if current else chunks


def wrap(text: str, max_chars: int) -> list:
    """One line, or two lines broken at the space nearest the middle."""
    if len(text) <= max_chars or " " not in text:
        return [text]
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    cut = min(spaces, key=lambda i: abs(i - len(text) / 2))
    return [text[:cut], text[cut + 1:]]


def write(cues: list, format: str) -> str:
    if format == "vtt":
        return "WEBVTT\n\n" + "".join(f"{stamp(a, '.')} --> {stamp(b, '.')}\n" + "\n".join(lines) + "\n\n"
                                      for a, b, lines in cues)
    return "".join(f"{n}\n{stamp(a, ',')} --> {stamp(b, ',')}\n" + "\n".join(lines) + "\n\n"
                   for n, (a, b, lines) in enumerate(cues, 1))


def stamp(seconds: float, separator: str) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3_600_000:02}:{ms // 60_000 % 60:02}:{ms // 1000 % 60:02}{separator}{ms % 1000:03}"


TIME = r"(\d+):(\d{2}):(\d{2})[,.](\d{3})|(\d{2}):(\d{2})[,.](\d{3})"


def read(path: Path) -> list:
    """Reads an .srt or .vtt file back into [(start, end, [lines])]."""
    cues = []
    for block in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n")):
        lines = block.strip().split("\n")
        for i, line in enumerate(lines):
            times = re.findall(TIME, line)
            if "-->" in line and len(times) == 2:
                cues.append((seconds_of(times[0]), seconds_of(times[1]), [l for l in lines[i + 1:] if l.strip()]))
                break
    return cues


def seconds_of(match: tuple) -> float:
    h, m, s, ms, m2, s2, ms2 = match
    if h:
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    return int(m2) * 60 + int(s2) + int(ms2) / 1000


def window(cues: list, start: float, end: float) -> list:
    """The cues seen between start and end, with times counted from start (for a clip)."""
    return [(max(a, start) - start, min(b, end) - start, lines) for a, b, lines in cues if b > start and a < end]
