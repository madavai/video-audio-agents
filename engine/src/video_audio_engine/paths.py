"""Where things live: the person's output folders and the engine's private data folder."""
import os
import re
import sys
from pathlib import Path


def data_dir() -> Path:
    """Private engine state (models, browser login profile, log). Claude Code passes its plugin data folder as VAA_DATA."""
    value = os.environ.get("VAA_DATA", "")
    if not value or "${" in value:  # not set, or not substituted by an older Claude Code
        value = Path.home() / ".claude" / "plugins" / "data" / "video-audio-agents-madavai"
    path = Path(value)
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    """The person's real Documents folder (on Windows it is often moved into OneDrive)."""
    if sys.platform == "win32":
        try:
            import winreg
            key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                return Path(os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0]))
        except OSError:
            pass
    return Path.home() / "Documents"


def output_root() -> Path:
    """Where everything made for the person goes: one folder per link inside it."""
    return documents_dir() / "VideoAudioAgents"


def safe_name(name: str, fallback: str = "untitled", limit: int = 60) -> str:
    """A file or folder name that works on every computer: no forbidden characters, at most `limit` long.
    Titles name both the folder and the files in it, so 60 keeps whole paths under Windows' 260 limit."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", name).strip().rstrip(".")[:limit].strip()
    return name or fallback


def free_name(folder: Path, name: str, exts) -> str:
    """A name with none of these extensions used yet: "name", then "name (2)", "name (3)"...
    For files made together (an .mp4 and its .mp3), so they keep the same name."""
    folder, name = Path(folder), safe_name(name, limit=100)  # room for a label such as " (summary)"
    candidate, n = name, 2
    while any((folder / f"{candidate}{ext}").exists() for ext in exts):
        candidate, n = f"{name} ({n})", n + 1
    return candidate


def free_path(folder: Path, name: str, ext: str) -> Path:
    """A path not used yet: "name.mp3", then "name (2).mp3", "name (3).mp3"... Never overwrites."""
    return Path(folder) / f"{free_name(folder, name, [ext])}{ext}"
