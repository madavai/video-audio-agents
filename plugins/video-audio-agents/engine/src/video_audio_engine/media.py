"""fetch_media: download the video, the audio or both from a link, into one folder per link."""
import logging
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp
from mcp.server.mcpserver.exceptions import ToolError

from . import browser, models, paths
from .progress import Stopped
from .setup_check import find_deno

log = logging.getLogger("engine.media")
KEEP = {"audio": [".mp3"], "video": [".mp4"], "both": [".mp4", ".mp3"]}  # the finished files per choice
WHAT = {"audio": "the audio", "video": "the video", "both": "the video and audio"}
AGENT = f"video-audio-agents (https://github.com/madavai/video-audio-agents) yt-dlp/{yt_dlp.version.__version__}"


class ToLog:
    """yt-dlp's messages go to the log file, never to the screen (stdout carries the MCP messages)."""

    def debug(self, msg):
        log.debug(msg)

    def info(self, msg):
        log.info(msg)

    def warning(self, msg):
        log.warning(msg)

    def error(self, msg):
        log.error(msg)


def fetch_media(job, url: str, save: str, folder: str | None = None) -> dict:
    job.report(0, "Getting ready")
    ffmpeg = models.ensure_ffmpeg(lambda pct, msg: job.report(0, msg))  # a one-time download if setup didn't
    stream, cookies, referer = url, None, None
    try:
        title = read_link(url)
    except yt_dlp.utils.DownloadError as e:
        if "DRM" in str(e):
            raise ToolError("This video is copy-protected (DRM), and copy-protected videos aren't supported.") from e
        if "HTTP Error 404" in str(e) or "HTTP Error 410" in str(e):
            raise ToolError("This link doesn't exist any more (the site says \"not found\"). Check the link.") from e
        if "getaddrinfo" in str(e) or "Name or service not known" in str(e) or "nodename nor servname" in str(e):
            raise ToolError("This site can't be reached. Check the link and the internet connection.") from e
        log.info("Not directly downloadable, opening it in the browser: %s", e)
        found = browser.find_stream(job, url)
        stream, title, cookies, referer = found["stream"], found["title"], found["cookies"], found["referer"]

    short = paths.safe_name(title or "download")
    target = Path(folder or paths.output_root()) / short
    target.mkdir(parents=True, exist_ok=True)
    name = paths.free_name(target, short, [".mp4", ".mp3", ".txt", ".segments.json"])
    before = set(target.iterdir())
    with tempfile.TemporaryDirectory() as tmp:
        opts = options(job, save, str(target / name), ffmpeg) | {"http_headers": identify(stream)}
        if cookies:
            cookie_file = Path(tmp) / "cookies.txt"
            cookie_file.write_text(cookies, encoding="utf-8")
            opts.update(cookiefile=str(cookie_file), http_headers={**identify(stream), "Referer": referer})
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([stream])
        except Stopped:
            tidy_up(target, before, name, save)
            raise
        except yt_dlp.utils.DownloadError as e:
            tidy_up(target, before, name, save)
            raise ToolError(f"The download failed ({str(e).removeprefix('ERROR: ')}).") from e
    tidy_up(target, before, name, save)  # the separate picture and sound pieces kept for the mp3
    files = [str(target / f"{name}{ext}") for ext in KEEP[save] if (target / f"{name}{ext}").exists()]
    if not files:
        raise ToolError("The download finished but no file came out of it. Try again, or try save = \"both\".")
    job.report(100, "Downloaded")
    return {"title": title, "folder": str(target), "files": files, "used_browser": cookies is not None}


def read_link(url: str) -> str:
    """The title, if the downloader understands the link by itself (YouTube, Vimeo, direct files and many more)."""
    with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, "logger": ToLog(), "http_headers": identify(url),
                           **js_runtime()}) as ydl:
        return ydl.extract_info(url, download=False).get("title")


def identify(url: str) -> dict:
    """Wikimedia (Wikipedia, Commons) turns away programs that pretend to be a web browser and asks them to say who
    they are. Every other site keeps the downloader's usual browser-like headers (an empty dict changes nothing)."""
    host = urlsplit(url).hostname or ""
    return {"User-Agent": AGENT} if host.endswith((".wikimedia.org", ".wikipedia.org")) else {}


def options(job, save: str, base: str, ffmpeg: Path) -> dict:
    """The downloader's settings: what to fetch, where to put it, and reporting progress (which also stops it)."""
    def progress(d):
        job.check()
        if d["status"] != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if d.get("fragment_count"):  # streams arrive in numbered pieces
            pct = d.get("fragment_index", 0) / d["fragment_count"] * 100
        elif total:
            pct = d["downloaded_bytes"] / total * 100
        else:
            return
        job.report(pct * 0.95, f"Downloading {WHAT[save]}... {int(pct)}%")

    def converting(d):
        job.check()
        steps = {"Merger": "Joining video and sound", "VideoConvertor": "Converting the video to mp4",
                 "ExtractAudio": "Making the mp3"}
        if d["status"] == "started" and d["postprocessor"] in steps:
            job.report(96, steps[d["postprocessor"]])

    opts = {"outtmpl": base + ".%(ext)s", "noplaylist": True, "quiet": True, "noprogress": True, "logger": ToLog(),
            "ffmpeg_location": str(ffmpeg), "progress_hooks": [progress], "postprocessor_hooks": [converting],
            "postprocessors": [], **js_runtime()}
    if save == "audio":
        opts["format"] = "ba/b"
    else:  # the best picture in formats every player opens; anything else is converted to mp4
        opts.update(format="bv*+ba/b", format_sort=["vcodec:h264", "ext:mp4:m4a", "res", "acodec:m4a"],
                     merge_output_format="mp4")
        opts["postprocessors"].append({"key": "FFmpegVideoConvertor", "preferedformat": "mp4"})
    if save in ("audio", "both"):
        opts["postprocessors"].append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3"})
        opts["keepvideo"] = save == "both"
    return opts


def js_runtime() -> dict:
    """YouTube needs a JavaScript runtime; the engine brings its own copy of Deno."""
    deno = find_deno()
    return {"js_runtimes": {"deno": {"path": deno}}} if deno else {}


def tidy_up(target: Path, before: set, name: str, save: str) -> None:
    """Removes the in-between and half-made files of this download (after it finished, stopped or failed);
    keeps the finished files and anything that was in the folder before."""
    finished = {f"{name}{ext}" for ext in KEEP[save]}
    for path in set(target.iterdir()) - before:
        if path.name not in finished:
            path.unlink(missing_ok=True)
    if not any(target.iterdir()):
        target.rmdir()
