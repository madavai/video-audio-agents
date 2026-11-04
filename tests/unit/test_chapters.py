import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import audio


def marks(tmp_path, text, length=7200):
    file = tmp_path / "Talk (chapters).md"
    file.write_text(text, encoding="utf-8")
    return audio.chapter_marks(file, length)


def test_every_way_the_transcriber_may_write_a_chapter_is_read(tmp_path):
    text = ("# Chapters\n\n"
            "00:00 Welcome\n"
            "- 01:30 - The first topic\n"
            "* **02:45** Bold time: with a colon\n"
            "3. [4:05] Numbered and bracketed\n"
            "1:02:03 – An hour in\n"
            "Not a chapter line\n")
    assert marks(tmp_path, text) == [(0, "Welcome"), (90, "The first topic"), (165, "Bold time: with a colon"),
                                     (245, "Numbered and bracketed"), (3723, "An hour in")]


def test_chapters_are_put_in_order_and_a_missing_title_gets_a_number(tmp_path):
    assert marks(tmp_path, "05:00 Later\n00:00\n") == [(0, "Chapter 2"), (300, "Later")]


def test_chapters_must_fit_the_audio(tmp_path):
    with pytest.raises(ToolError, match='"Late" starts at 1:00, but the audio is only 0:45 long'):
        marks(tmp_path, "00:00 Early\n01:00 Late\n", length=45)
    with pytest.raises(ToolError, match="Two chapters start at 0:10"):
        marks(tmp_path, "00:10 One\n00:10 Two\n")
    with pytest.raises(ToolError, match="There are no chapters in Talk"):
        marks(tmp_path, "just words\n")
