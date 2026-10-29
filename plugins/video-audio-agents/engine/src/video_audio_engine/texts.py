"""save_text: saves what the AI wrote (translations, summaries, chapters, notes, posts) next to the file it came
from, as "name (label).ext". Long texts can be saved in parts: the later parts are appended. Titles, X posts,
Shorts titles and quote cards longer than their limit are refused, so every draft can be pasted as it is.
translated_segments: pairs a translated transcript with the original timings, checking nothing was lost (and, for
dubbing, that every line can be said in its time).
search_texts: finds where something was said, across all the transcripts."""
import json
import re
from collections import Counter
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import paths

SEGMENTS = ".segments.json"


def x_length(post: str) -> int:
    """A post's length as X counts it: 1 for most characters (Latin, Indian scripts, dashes, quotes), 2 for
    Chinese, Japanese, Korean and emoji."""
    return sum(1 if ord(c) <= 0x10FF or 0x2000 <= ord(c) <= 0x200D or 0x2010 <= ord(c) <= 0x201F
               or 0x2032 <= ord(c) <= 0x2037 else 2 for c in post)


# Drafts with a length limit, by label: what one piece is called, how the text is split into pieces, the limit,
# how it is counted, and the limit in words for the message. A draft's translation has the same limit: saved next to
# the draft ("Lesson (x-thread).txt", label "Hindi") or labelled with it ("x-thread Hindi").
LIMITS = {
    "titles": ("Title", lambda text: text.split("\n"), 60, len, "the 60 characters YouTube shows in full"),
    "x-thread": ("X post", lambda text: re.split(r"\n\s*\n", text), 280, x_length,
                 "X's limit of 280 (posts are separated by a blank line)"),
    "shorts": ("Short's title", lambda text: re.findall(r"(?im)^\s*title:(.*)$", text), 40, len,
               "the 40 characters a Short's title shows in full on a phone"),
    "quote-cards": ("Quote card", lambda text: text.split("\n"), 120, len,
                    "the 120 characters that fit on a square card"),
    # A calendar's X posts: the text under each "Day 3 (X)" line, up to the next day.
    "calendar": ("X post", lambda text: re.findall(r"(?ims)^\s*day \d+ \(x\)[^\n]*\n(.*?)(?=^\s*day \d+ \(|\Z)", text),
                 280, x_length, "X's limit of 280"),
}
LABELS = re.compile(r"\(([^()]+)\)")  # "Lesson (x-thread) (Hindi) (2)" → x-thread, Hindi, 2


def check_limits(label: str, text: str) -> None:
    """Refuses the whole text, naming the first piece that is too long, before anything is written."""
    key = label.strip().lower().replace(" ", "-")
    rule = next((LIMITS[name] for name in LIMITS if key == name or key.startswith(name + "-")), None)
    if not rule:
        return
    piece, pieces, limit, length, words = rule
    for number, part in enumerate((p.strip() for p in pieces(text) if p.strip()), 1):
        if length(part) > limit:
            start = " ".join(part.split())[:40].rstrip()
            raise ToolError(f'{piece} {number} ("{start}...") is {length(part)} characters, over {words}; '
                            "shorten it and save again.")


def save_text(next_to: str, label: str, text: str, ext: str, append_to: str | None = None) -> dict:
    if append_to:
        return {"file": str(append(Path(append_to), text))}
    source = Path(next_to)
    for each in [label, *LABELS.findall(source.stem)]:
        check_limits(each, text)
    root = paths.output_root()
    if not source.parent.is_dir():
        if source.parent != root and root not in source.parent.parents:
            raise ToolError(f"The folder {source.parent} doesn't exist.")
        source.parent.mkdir(parents=True)  # e.g. the glossary, before anything was downloaded
    base = source.name.removesuffix(SEGMENTS) if source.name.endswith(SEGMENTS) else source.stem
    # Translated segments stay recognisable as segments, so subtitles and dubbing can be made from them.
    suffix = SEGMENTS if ext == "json" and source.name.endswith(SEGMENTS) else f".{ext}"
    if ext == "json":
        data = read_json(text, suffix == SEGMENTS)
        text = json.dumps(data, ensure_ascii=False, indent=1)
    # No label: saved under next_to's own name (e.g. glossary.md), still never overwriting.
    name = f"{base} ({paths.safe_name(label, 'text', limit=30)})" if label.strip() else base
    path = paths.free_path(source.parent, name, suffix)
    path.write_text(text if text.endswith("\n") or ext == "json" else text + "\n", encoding="utf-8")
    return {"file": str(path)}


def append(path: Path, text: str) -> Path:
    """Adds a later part: text goes on the end; a JSON list is extended with the new list."""
    if not path.is_file():
        raise ToolError(f"There is no file at {path} to add to. Save the first part without append_to.")
    for each in LABELS.findall(path.stem):
        check_limits(each, text)
    if path.suffix == ".json":
        old = read_json(path.read_text(encoding="utf-8"), path.name.endswith(SEGMENTS))
        new = read_json(text, path.name.endswith(SEGMENTS))
        if not (isinstance(old, list) and isinstance(new, list)):
            raise ToolError("Only a list can be added to a .json file.")
        path.write_text(json.dumps(old + new, ensure_ascii=False, indent=1), encoding="utf-8")
        return path
    with open(path, "a", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    return path


def read_json(text: str, segments: bool):
    """Parses JSON; for a segments file also checks every item has a start, an end and a text."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ToolError(f"That isn't valid JSON ({e.msg} at line {e.lineno}).") from e
    if segments:
        if not isinstance(data, list) or not all(
                isinstance(s, dict) and isinstance(s.get("start"), (int, float))
                and isinstance(s.get("end"), (int, float)) and isinstance(s.get("text"), str) for s in data):
            raise ToolError('A segments file must be a list of {"start": seconds, "end": seconds, "text": "..."}.')
    return data


STAMPED = re.compile(r"^\s*\[(\d+(?:\.\d+)?)s\]\s*(.*)$")


def translated_segments(segments_file: str, translated_file: str, dub_language: str | None = None) -> dict:
    """The original segments with their text replaced by the translation, matched by the "[12.5s]" time on each
    translated line. Every original line must have its translation, so nothing is lost. A line saved again with
    the same time replaces the earlier one (a shorter wording for dubbing). If the lines were saved out of order
    (a missed line added at the end) or replaced, the translated file is put back in order.
    For dubbing (dub_language), lines that would take longer to say than their time are returned instead, so they
    can be shortened before the slow speaking; nothing is saved until every line fits."""
    original = read_json(existing(segments_file).read_text(encoding="utf-8"), segments=True)
    translated = existing(translated_file)
    lines = stamped_lines(translated.read_text(encoding="utf-8"))
    if not lines:
        raise ToolError(f'{translated.name} has no "[12.5s] text" lines. Translate the transcript line by line, '
                        "keeping each line's time.")
    waiting, wanted = {}, Counter(f"{float(s['start']):.1f}" for s in original)
    for key, text in lines:
        waiting.setdefault(key, []).append(text)
    for key, said in waiting.items():
        if key in wanted:
            del said[:-wanted[key]]  # only the last wording of a line counts
    result, missing = [], []
    for segment in original:
        key = f"{float(segment['start']):.1f}"
        if waiting.get(key):
            result.append({**segment, "text": waiting[key].pop(0)})
        else:
            missing.append(f"[{key}s]")
    extra = [f"[{key}s]" for key, texts in waiting.items() for _ in texts]
    if missing or extra:
        def some(times):
            return ", ".join(times[:10]) + (" ..." if len(times) > 10 else "")
        problems = ([f"{len(missing)} line(s) missing: {some(missing)}"] if missing else []) + \
                   ([f"{len(extra)} line(s) with a time the transcript doesn't have: {some(extra)}"] if extra else [])
        raise ToolError(f"The translation doesn't match the transcript line for line ({'; '.join(problems)}). "
                        "Add the missing lines with append_to (any order is fine) or fix the times, then try again.")
    if [key for key, _ in lines] != [f"{float(s['start']):.1f}" for s in original]:
        translated.write_text("".join(f"[{float(s['start']):.1f}s] {s['text']}\n" for s in result), encoding="utf-8")
    if dub_language:
        from .speech import too_long  # here, because speech uses this module
        long = too_long(result, dub_language)
        if long:
            return {"too_long": long[:50], "too_long_count": len(long), "lines": len(result)}
    path = paths.free_path(translated.parent, translated.stem, SEGMENTS)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"segments_file": str(path), "lines": len(result)}


def stamped_lines(text: str) -> list:
    """[(time, text)] from "[12.5s] text" lines. A line without a time continues the line before it;
    a time with no text counts as missing."""
    lines = []
    for raw in text.splitlines():
        match = STAMPED.match(raw)
        if match:
            lines.append([f"{float(match[1]):.1f}", match[2].strip()])
        elif raw.strip() and lines:
            lines[-1][1] = f"{lines[-1][1]} {raw.strip()}".strip()
    return [(key, text) for key, text in lines if text]


MATCHES = 50  # matches listed per search; match_count says how many there are


def search_texts(query: str, folder: str | None = None) -> dict:
    """The lines of the transcripts (every .txt file under folder) that hold all the words of query, in any case,
    with the time of each line in the recording (its "[12.5s]" stamp, if it has one)."""
    root = Path(folder) if folder else paths.output_root()
    if not root.is_dir():
        raise ToolError(f"The folder {root} doesn't exist." if folder else "There are no transcripts yet.")
    words = query.casefold().split()
    if not words:
        raise ToolError("Say what to search for.")
    from .clips import clock  # here, because clips uses this module
    matches, count, files = [], 0, 0
    for file in sorted(root.rglob("*.txt")):
        files += 1
        for number, line in enumerate(file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            folded = line.casefold()
            if not all(word in folded for word in words):
                continue
            count += 1
            if len(matches) < MATCHES:
                stamp = STAMPED.match(line)
                matches.append({"file": str(file), "line": number, "at": clock(float(stamp[1])) if stamp else None,
                                "text": excerpt(line.strip(), folded.strip().find(words[0]))})
    return {"matches": matches, "match_count": count, "files_searched": files}


def excerpt(line: str, at: int, size: int = 200) -> str:
    """A long line (a paragraph, when a transcript has no times) cut to the part around the match."""
    if len(line) <= size:
        return line
    start = max(0, min(at - size // 3, len(line) - size))
    return ("..." if start else "") + line[start:start + size] + ("..." if start + size < len(line) else "")


def existing(file: str) -> Path:
    path = Path(file)
    if not path.is_file():
        raise ToolError(f"There is no file at {path}.")
    return path
