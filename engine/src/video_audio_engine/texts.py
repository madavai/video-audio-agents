"""save_text: saves what the AI wrote (translations, summaries, chapters, notes, posts) next to the file it came
from, as "name (label).ext". Long texts can be saved in parts: the later parts are appended.
translated_segments: pairs a translated transcript with the original timings, checking nothing was lost."""
import json
import re
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import paths

SEGMENTS = ".segments.json"


def save_text(next_to: str, label: str, text: str, ext: str, append_to: str | None = None) -> dict:
    if append_to:
        return {"file": str(append(Path(append_to), text))}
    source = Path(next_to)
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


def translated_segments(segments_file: str, translated_file: str) -> dict:
    """The original segments with their text replaced by the translation, matched by the "[12.5s]" time on each
    translated line. Every original line must have its translation, so nothing is lost. If the lines were
    saved out of order (a missed line added at the end), the translated file is put back in order."""
    original = read_json(existing(segments_file).read_text(encoding="utf-8"), segments=True)
    translated = existing(translated_file)
    lines = stamped_lines(translated.read_text(encoding="utf-8"))
    if not lines:
        raise ToolError(f'{translated.name} has no "[12.5s] text" lines. Translate the transcript line by line, '
                        "keeping each line's time.")
    waiting = {}
    for key, text in lines:
        waiting.setdefault(key, []).append(text)
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


def existing(file: str) -> Path:
    path = Path(file)
    if not path.is_file():
        raise ToolError(f"There is no file at {path}.")
    return path
