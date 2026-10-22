"""The models and helper programs the engine downloads: what each is, how big, where it lives,
and downloading it with progress and resume. Every download in the engine goes through here."""
import http.client
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

from .paths import data_dir

GB = 1024**3
HUGGING_FACE = "https://huggingface.co"
CHATTERBOX = ("ResembleAI/chatterbox", "5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18")

# Each model: a plain name for messages, its Hugging Face repo at a fixed version, and its files with exact sizes.
# The three Chatterbox models share one folder (and some files), so a shared file is downloaded once.
MODELS = {
    "base": {
        "label": "speech-to-text, fast",
        "repo": ("Systran/faster-whisper-base", "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"),
        "files": {"config.json": 2309, "model.bin": 145217532, "tokenizer.json": 2203239, "vocabulary.txt": 459861},
    },
    "small": {
        "label": "speech-to-text, balanced",
        "repo": ("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120"),
        "files": {"config.json": 2370, "model.bin": 483546902, "tokenizer.json": 2203239, "vocabulary.txt": 459861},
    },
    "large-v3-turbo": {
        "label": "speech-to-text, accurate",
        "repo": ("mobiuslabsgmbh/faster-whisper-large-v3-turbo", "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"),
        "files": {"config.json": 2263, "model.bin": 1617884929, "preprocessor_config.json": 340,
                  "tokenizer.json": 2710337, "vocabulary.json": 1068114},
    },
    "voice": {
        "label": "voice changer",
        "repo": CHATTERBOX,
        "files": {"s3gen.safetensors": 1056484620, "conds.pt": 107374},
    },
    "english": {
        "label": "English speech in a saved voice",
        "repo": CHATTERBOX,
        "files": {"ve.safetensors": 5695784, "t3_cfg.safetensors": 2129653744, "s3gen.safetensors": 1056484620,
                  "tokenizer.json": 25470, "conds.pt": 107374},
    },
    "multilingual": {
        "label": "Hindi, French and Spanish speech in a saved voice",
        "repo": CHATTERBOX,
        "files": {"ve.pt": 5698626, "t3_mtl23ls_v2.safetensors": 2143989752, "s3gen.pt": 1057165844,
                  "grapheme_mtl_merged_expanded_v1.json": 69989, "conds.pt": 107374, "Cangjie5_TC.json": 1920163},
    },
}
STANDARD = ["base", "small"]
FULL = STANDARD + ["large-v3-turbo", "voice", "english", "multilingual"]
FFMPEG_GB = 0.1  # about; the exact size comes with the download
# The one big model in memory, kept for the next job: {name: model}. Speech-to-text and the voice models share it,
# and each clears it before loading another, so the computer keeps enough memory.
loaded = {}


def models_dir() -> Path:
    return data_dir() / "models"


def folder(name: str) -> Path:
    """Where a model's files live, e.g. <data>/models/faster-whisper-small."""
    return models_dir() / MODELS[name]["repo"][0].split("/")[1]


def missing_files(names) -> dict:
    """{path: (url, size)} for every file of these models that isn't fully downloaded. Shared files appear once."""
    base = os.environ.get("VAA_MODELS_URL", HUGGING_FACE).rstrip("/")
    missing = {}
    for name in names:
        repo, revision = MODELS[name]["repo"]
        for file, size in MODELS[name]["files"].items():
            path = folder(name) / file
            if not (path.exists() and path.stat().st_size == size):
                missing[path] = (f"{base}/{repo}/resolve/{revision}/{file}", size)
    return missing


def missing_gb(names) -> float:
    """How many GB still have to be downloaded for these models, rounded to one decimal."""
    return round(sum(size for _, size in missing_files(names).values()) / GB, 1)


def is_present(name: str) -> bool:
    return not missing_files([name])


def ensure(names, report=None) -> None:
    """Downloads whatever is missing of these models. `report(percent, message)` gets progress."""
    missing = missing_files(names)
    total, done = sum(size for _, size in missing.values()) or 1, 0
    labels = ", ".join(MODELS[n]["label"] for n in names if not is_present(n))
    for path, (url, size) in missing.items():
        def file_report(got, _size, done=done):
            if report:
                pct = (done + got) / total * 100
                report(pct, f"Downloading {labels} ({(done + got) / GB:.1f} of {total / GB:.1f} GB)")
        download(url, path, size, file_report)
        done += size


def download(url: str, path: Path, size: int | None, report=None) -> None:
    """Downloads `url` to `path`, resuming a half-finished download (kept as `<path>.part`).
    The file only appears under its real name once it is complete."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(url, headers={"User-Agent": "video-audio-agents"})
    if have:
        request.add_header("Range", f"bytes={have}-")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if have and response.status != 206:  # the server ignored the resume request: start again
                have = 0
            size = size or have + int(response.headers.get("Content-Length") or 0)
            with open(part, "ab" if have else "wb") as f:
                while chunk := response.read(1024 * 1024):
                    f.write(chunk)
                    have += len(chunk)
                    if report:
                        report(have, size)
    except (OSError, http.client.HTTPException) as e:
        raise ConnectionError(f"The download of {path.name} stopped ({e}). "
                              "Try again: it continues where it stopped.") from e
    if size and have != size:
        raise ConnectionError(f"The download of {path.name} stopped early. Try again: it continues where it stopped.")
    os.replace(part, path)


def ffmpeg_dir() -> Path:
    """Where ffmpeg and ffprobe live: inside the data folder, so they survive plugin updates."""
    from static_ffmpeg import run
    return data_dir() / "bin" / run.get_platform_key()


def ffmpeg_present() -> bool:
    exe = ".exe" if sys.platform == "win32" else ""
    return all((ffmpeg_dir() / f"{tool}{exe}").exists() for tool in ("ffmpeg", "ffprobe"))


def ensure_ffmpeg(report=None) -> Path:
    """Downloads ffmpeg and ffprobe once (about 50 to 140 MB, depending on the computer), then puts them on PATH."""
    from static_ffmpeg import run
    where = ffmpeg_dir()
    if not ffmpeg_present():
        archive = where.with_suffix(".zip")
        download(run.get_platform_http_zip(), archive, None,
                 report and (lambda got, size: report(got / (size or 1) * 100, "Downloading ffmpeg (the video tool)")))
        with zipfile.ZipFile(archive) as z:  # the archive holds a folder named like `where`
            z.extractall(where.parent)
        archive.unlink()
        if sys.platform != "win32":
            for tool in ("ffmpeg", "ffprobe"):
                (where / tool).chmod(0o755)
    if str(where) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(where) + os.pathsep + os.environ.get("PATH", "")
    return where


def which_ffmpeg() -> str | None:
    """ffmpeg's location without downloading anything: ours if present, else one already on the computer."""
    exe = ".exe" if sys.platform == "win32" else ""
    if ffmpeg_present():
        return str(ffmpeg_dir() / f"ffmpeg{exe}")
    return shutil.which("ffmpeg")
