"""search_texts: where something was said, across the transcripts in the (fake) Documents folder."""
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import paths, texts


def transcript(folder, name, text):
    path = paths.output_root() / folder / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_finds_the_line_and_its_time_across_transcripts():
    talk = transcript("Talk", "Talk", "[0.3s] And so, my fellow Americans,\n[3.1s] ask not what your country\n"
                                      "[125.4s] can do for you, ask what you can do for your Country.\n")
    lesson = transcript("Course/Lesson 1", "Lesson 1", "[2.0s] Today: the moon.\n[64.0s] Why your COUNTRY matters.\n")
    transcript("Course/Lesson 1", "Lesson 1 (summary)", "Nothing about it here.\n")
    result = texts.search_texts("country")
    assert result["match_count"] == 3 and result["files_searched"] == 3
    assert result["matches"] == [  # case doesn't matter; files in name order, lines in order
        {"file": lesson, "line": 2, "at": "1:04", "text": "[64.0s] Why your COUNTRY matters."},
        {"file": talk, "line": 2, "at": "0:03", "text": "[3.1s] ask not what your country"},
        {"file": talk, "line": 3, "at": "2:05",
         "text": "[125.4s] can do for you, ask what you can do for your Country."}]


def test_every_word_in_any_order_and_a_folder_of_its_own(tmp_path):
    transcript("Talk", "Talk", "[0.3s] And so, my fellow Americans,\n")
    assert [m["at"] for m in texts.search_texts("americans FELLOW")["matches"]] == ["0:00"]
    assert texts.search_texts("fellow citizens")["matches"] == []
    other = tmp_path / "Recordings"
    other.mkdir()
    (other / "Call.txt").write_text("We agreed on the budget.\n", encoding="utf-8")
    result = texts.search_texts("budget", str(other))
    assert result["matches"] == [{"file": str(other / "Call.txt"), "line": 1, "at": None,
                                  "text": "We agreed on the budget."}]  # a transcript without times


def test_long_paragraphs_and_many_matches_stay_small():
    paragraph = "word " * 300 + "the moon landing " + "word " * 300
    transcript("Notes", "Notes", paragraph + "\n" + "[1.0s] moon\n" * 80)
    result = texts.search_texts("moon")
    assert result["match_count"] == 81 and len(result["matches"]) == texts.MATCHES
    first = result["matches"][0]["text"]
    assert "the moon landing" in first and len(first) <= 206 and first.startswith("...") and first.endswith("...")


def test_nothing_to_search():
    with pytest.raises(ToolError, match="no transcripts yet"):
        texts.search_texts("moon")
    with pytest.raises(ToolError, match="doesn't exist"):
        texts.search_texts("moon", str(paths.output_root() / "nowhere"))
    transcript("Talk", "Talk", "[0.3s] Hello\n")
    with pytest.raises(ToolError, match="what to search for"):
        texts.search_texts("  ")
