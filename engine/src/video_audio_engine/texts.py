"""save_text: saves what the AI wrote (translations, summaries, chapters, notes, posts) next to the file it came
from, as "name (label).ext". Long texts can be saved in parts: the later parts are appended."""
import json
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import paths

SEGMENTS = ".segments.json"


def save_text(next_to: str, label: str, text: str, ext: str, append_to: str | None = None) -> dict:
    if append_to:
        return {"file": str(append(Path(append_to), text))}
    source = Path(next_to)
    if not source.parent.is_dir():
        raise ToolError(f"The folder {source.parent} doesn't exist.")
    base = source.name.removesuffix(SEGMENTS) if source.name.endswith(SEGMENTS) else source.stem
    # Translated segments stay recognisable as segments, so subtitles and dubbing can be made from them.
    suffix = SEGMENTS if ext == "json" and source.name.endswith(SEGMENTS) else f".{ext}"
    if ext == "json":
        data = read_json(text, suffix == SEGMENTS)
        text = json.dumps(data, ensure_ascii=False, indent=1)
    path = paths.free_path(source.parent, f"{base} ({paths.safe_name(label, 'text', limit=30)})", suffix)
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
