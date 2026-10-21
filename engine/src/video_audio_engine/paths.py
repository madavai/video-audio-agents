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


def safe_name(name: str, fallback: str = "untitled") -> str:
    """A file or folder name that works on every computer: no forbidden characters, at most 80 long."""
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", name).strip().rstrip(".")[:80].strip()
    return name or fallback


def free_path(folder: Path, name: str, ext: str) -> Path:
    """A path not used yet: "name.mp3", then "name (2).mp3", "name (3).mp3"... Never overwrites."""
    folder, name = Path(folder), safe_name(name)
    path, n = folder / f"{name}{ext}", 2
    while path.exists():
        path, n = folder / f"{name} ({n}){ext}", n + 1
    return path
