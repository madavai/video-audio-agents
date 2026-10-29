"""list_links on a "playlist" page made at test time: a podcast feed served by the local web server."""
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import media, paths, progress


@pytest.fixture
def served(media):
    """The folder the local web server serves (the fixture "media" would hide the module of that name)."""
    return media


def feed(media_folder, web, name, items):
    """Writes a feed page listing the items (title, file) and returns its address."""
    entries = "".join(f'<item><title>{title}</title><enclosure url="{web}/{file}" type="audio/mpeg"/></item>'
                      for title, file in items)
    (media_folder / name).write_text(f'<?xml version="1.0"?><rss version="2.0"><channel><title>Lessons: week 1'
                                     f'</title>{entries}</channel></rss>', encoding="utf-8")
    return f"{web}/{name}"


def links(url, start=1):
    return media.list_links(progress.Job(), url, start)


def test_a_playlist_of_three_gives_three_links_and_three_folders(served, web, with_models):
    url = feed(served, web, "three.xml", [("JFK", "talk.mp3"), ("JFK again", "long.mp3"), ("A beep", "beep.mp3")])
    result = links(url)
    assert result["title"] == "Lessons: week 1" and result["total"] == 3 and result["first"] == 1
    assert result["links"] == [f"{web}/talk.mp3", f"{web}/long.mp3", f"{web}/beep.mp3"]
    assert result["titles"] == ["JFK", "JFK again", "A beep"]
    assert result["folder"] == str(paths.output_root() / "Lessons week 1")  # no ":" in a folder name
    for link in result["links"]:  # then the normal flow per link, kept together in the list's folder
        media.fetch_media(progress.Job(), link, "audio", result["folder"])
    assert sorted(p.name for p in paths.output_root().joinpath("Lessons week 1").iterdir()) == ["beep", "long", "talk"]


def test_a_long_list_comes_in_parts_and_says_how_many_there_are(served, web, with_models, monkeypatch):
    url = feed(served, web, "long.xml", [(f"Lesson {n}", f"lesson{n}.mp3") for n in range(1, 121)])
    first = links(url)
    assert first["total"] == 120 and len(first["links"]) == 50 and first["titles"][0] == "Lesson 1"
    last = links(url, start=101)
    assert last["first"] == 101 and last["titles"] == [f"Lesson {n}" for n in range(101, 121)]
    with pytest.raises(ToolError, match="only 120 videos"):
        links(url, start=121)
    monkeypatch.setattr(media, "COUNT_UP_TO", 80)  # a channel with thousands of videos isn't counted to the end
    assert links(url)["total"] == "more than 80"


def test_a_link_that_is_not_a_list(served, web, with_models):
    with pytest.raises(ToolError, match="single video, not a playlist"):
        links(f"{web}/talk.mp3")
    with pytest.raises(ToolError, match="no playlist or channel that can be read"):
        links(f"{web}/empty.html")
    with pytest.raises(ToolError, match="list is empty"):
        links(feed(served, web, "empty.xml", []))


def test_a_dead_link_gives_a_plain_error(web, with_models):
    with pytest.raises(ToolError, match="doesn't exist any more"):
        links(f"{web}/missing.xml")
