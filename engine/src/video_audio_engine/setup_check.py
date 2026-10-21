"""check_setup: a fast look at what is installed and what is missing. Downloads nothing."""
import os
import platform
import shutil
import sys
from pathlib import Path

from . import models
from .paths import data_dir, output_root

GB = 1024**3


def find_browser() -> str | None:
    """Edge or Chrome, used to open pages behind a login. None if neither is installed."""
    if sys.platform == "win32":
        roots = [os.environ.get(v, "") for v in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        places = {"edge": r"Microsoft\Edge\Application\msedge.exe", "chrome": r"Google\Chrome\Application\chrome.exe"}
        found = {name: any(r and Path(r, p).exists() for r in roots) for name, p in places.items()}
    elif sys.platform == "darwin":
        found = {"edge": Path("/Applications/Microsoft Edge.app").exists(),
                 "chrome": Path("/Applications/Google Chrome.app").exists()}
    else:
        found = {"edge": bool(shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")),
                 "chrome": bool(shutil.which("google-chrome") or shutil.which("google-chrome-stable"))}
    return next((name for name, ok in found.items() if ok), None)


def find_deno() -> str | None:
    try:
        import deno
        return deno.find_deno_bin()
    except (ImportError, FileNotFoundError):
        return shutil.which("deno")


def free_ram_gb() -> float:
    import psutil
    return round(psutil.virtual_memory().available / GB, 1)


def check_setup() -> dict:
    ffmpeg, deno, browser = models.which_ffmpeg(), find_deno(), find_browser()
    present = [name for name in models.FULL if models.is_present(name)]
    missing = {name: models.missing_gb([name]) for name in models.FULL if name not in present}
    ram, disk = free_ram_gb(), round(shutil.disk_usage(data_dir()).free / GB, 1)
    notes = []
    if not ffmpeg:
        notes.append(f"ffmpeg (the video tool, about {models.FFMPEG_GB} GB) isn't downloaded yet: run the setup.")
    if not deno:
        notes.append("Deno (needed for YouTube) is missing: run the setup again.")
    if not browser:
        notes.append("Neither Edge nor Chrome was found, so pages behind a login can't be opened.")
    if any(name in missing for name in models.STANDARD):
        notes.append("The speech-to-text models aren't downloaded yet: run the setup.")
    if ram < 6:
        notes.append(f"Only {ram} GB of memory is free; voice work needs about 6 GB.")
    if disk < 5:
        notes.append(f"Only {disk} GB of disk space is free; the models need up to 10 GB.")
    if shutil.which("nvidia-smi"):
        notes.append("An NVIDIA graphics card was found; using it to go faster comes in version 1.1.")
    return {
        "ok": bool(ffmpeg and deno) and all(name in present for name in models.STANDARD),
        "python": platform.python_version(),
        "ffmpeg": ffmpeg,
        "deno": deno,
        "browser": browser,
        "models_present": present,
        "models_missing_gb": missing,
        "free_ram_gb": ram,
        "free_disk_gb": disk,
        "gpu": bool(shutil.which("nvidia-smi")),
        "output_folder": str(output_root()),
        "notes": notes,
    }
