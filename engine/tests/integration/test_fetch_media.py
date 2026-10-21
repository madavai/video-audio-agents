"""fetch_media against a local web server with media made by ffmpeg at test time."""
import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import media, paths, progress
from video_audio_engine.setup_check import find_browser


class Job(progress.Job):
    """Collects the progress messages instead of sending them."""

    def __init__(self):
        super().__init__()
        self.messages = []

    def report(self, percent, message):
        super().report(percent, message)
        self.messages.append(message)


def fetch(url, save, folder=None):
    return media.fetch_media(Job(), url, save, folder)


def test_direct_mp3_link(web, with_models):
    result = fetch(f"{web}/talk.mp3", "audio")
    folder = paths.output_root() / "talk"
    assert result["title"] == "talk" and result["folder"] == str(folder)
    assert result["files"] == [str(folder / "talk.mp3")] and not result["used_browser"]
    assert sorted(p.name for p in folder.iterdir()) == ["talk.mp3"]


def test_direct_mp4_link_both_gives_video_and_audio(web, with_models, tmp_path):
    result = fetch(f"{web}/talk.mp4", "both", str(tmp_path / "elsewhere"))
    folder = tmp_path / "elsewhere" / "talk"
    assert result["files"] == [str(folder / "talk.mp4"), str(folder / "talk.mp3")]
    assert sorted(p.name for p in folder.iterdir()) == ["talk.mp3", "talk.mp4"]  # no leftover pieces


def test_hls_stream(web, with_models, tmp_path):
    result = fetch(f"{web}/hls/index.m3u8", "video", str(tmp_path))
    assert len(result["files"]) == 1 and result["files"][0].endswith(".mp4")
    assert [p.name for p in (tmp_path / result["title"]).iterdir()] == [result["title"] + ".mp4"]


def test_same_link_twice_is_never_overwritten(web, with_models, tmp_path):
    first = fetch(f"{web}/talk.mp3", "audio", str(tmp_path))
    second = fetch(f"{web}/talk.mp3", "audio", str(tmp_path))
    assert first["files"][0].endswith("talk.mp3") and second["files"][0].endswith("talk (2).mp3")


def test_stopping_midway_leaves_no_files(web, with_models, tmp_path):
    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith("Downloading"):
                        scope.cancel()
            await progress.run(Ctx(), media.fetch_media, f"{web}/slow.mp3", "audio", str(tmp_path / "out"))

    anyio.run(main)
    assert [p for p in (tmp_path / "out").rglob("*") if p.is_file()] == []


def test_a_dead_link_gives_a_plain_error_without_opening_a_browser(web, with_models, tmp_path, monkeypatch):
    monkeypatch.setattr("video_audio_engine.browser.find_stream", lambda *a: pytest.fail("opened a browser"))
    with pytest.raises(ToolError, match="doesn't exist any more"):
        fetch(f"{web}/missing.mp3", "audio", str(tmp_path))
    assert list(tmp_path.iterdir()) == []


needs_browser = pytest.mark.skipif(find_browser() is None, reason="needs Edge or Chrome")


@needs_browser
def test_a_page_whose_video_only_a_browser_finds(web, with_models, tmp_path, monkeypatch):
    monkeypatch.setenv("VAA_BROWSER_HEADLESS", "1")
    monkeypatch.setenv("VAA_BROWSER_WAIT", "30")
    result = fetch(f"{web}/lesson.html", "audio", str(tmp_path))
    assert result["used_browser"] and result["title"] == "Lesson one"
    assert result["files"] == [str(tmp_path / "Lesson one" / "Lesson one.mp3")]


@needs_browser
def test_a_page_without_video_or_audio(web, with_models, tmp_path, monkeypatch):
    monkeypatch.setenv("VAA_BROWSER_HEADLESS", "1")
    monkeypatch.setenv("VAA_BROWSER_WAIT", "4")
    with pytest.raises(ToolError, match="No video or audio was found"):
        fetch(f"{web}/empty.html", "audio", str(tmp_path))
    assert not (tmp_path / "Nothing here").exists()


def test_no_browser_on_the_computer(web, with_models, tmp_path, monkeypatch):
    monkeypatch.setattr("video_audio_engine.browser.find_browser", lambda: None)
    with pytest.raises(ToolError, match="neither Edge nor Chrome"):
        fetch(f"{web}/empty.html", "audio", str(tmp_path))


def test_cookies_are_written_in_the_downloaders_format():
    from video_audio_engine.browser import netscape
    text = netscape([{"domain": ".example.com", "path": "/", "secure": True, "expires": -1, "name": "s", "value": "1"}])
    assert text.splitlines() == ["# Netscape HTTP Cookie File", ".example.com\tTRUE\t/\tTRUE\t0\ts\t1"]
