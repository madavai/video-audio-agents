"""The graphics card. Transcripts run on an NVIDIA card once the setup's graphics-card option has installed NVIDIA's
maths library (cuBLAS): faster-whisper brings the rest. Voice, the music keeper and speaker labels stay on the
processor: they run on PyTorch 2.6 (pinned by the voice models), which has no code for the newest cards (RTX 50)."""
import ctypes
import functools
import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("engine")
failed = None  # what went wrong, once the card failed in this session: it isn't tried again until a restart


@functools.cache
def card() -> str | None:
    """The NVIDIA card's name, asked of nvidia-smi (it comes with NVIDIA's driver), or None."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return None
    try:
        said = subprocess.run([smi, "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True,
                              timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return said.splitlines()[0].strip() if said else None


def installed() -> bool:
    """Whether the setup's graphics-card option is installed (NVIDIA's library in the engine's environment)."""
    try:
        return importlib.util.find_spec("nvidia.cublas") is not None
    except ModuleNotFoundError:  # no nvidia package at all
        return False


@functools.cache
def libraries_found() -> bool:
    """Lets faster-whisper find NVIDIA's library: Windows looks for DLLs on PATH (cuBLAS loads its helpers by name),
    Linux gets them loaded first. False when they aren't installed or don't load."""
    if not installed():
        return False
    try:
        for root in importlib.util.find_spec("nvidia").submodule_search_locations:
            if sys.platform == "win32":
                for folder in Path(root).glob("*/bin"):
                    os.add_dll_directory(str(folder))
                    os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
            else:  # cuBLASLt first: cuBLAS needs it
                for library in sorted(Path(root).glob("*/lib/lib*.so*"), key=lambda p: "Lt" not in p.name):
                    ctypes.CDLL(str(library), mode=ctypes.RTLD_GLOBAL)
        return True
    except OSError as e:
        log.warning("NVIDIA's libraries didn't load: %s", e)
        return False


def usable() -> bool:
    """Whether transcripts can use the card now: a card, the graphics-card option, CUDA working, no failure yet."""
    if failed or not card() or not libraries_found():
        return False
    import ctranslate2
    return ctranslate2.get_cuda_device_count() > 0


def give_up(error: BaseException) -> str:
    """Notes that the card failed (details to the log) and returns the one line the person reads."""
    global failed
    failed = str(error) or type(error).__name__
    log.warning("The graphics card failed, using the processor: %s", failed, exc_info=error)
    return "The graphics card couldn't be used this time, so this ran on the processor (slower)."
