import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import texts


def test_saved_next_to_the_source_with_its_label(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("hello")
    first = texts.save_text(str(source), "summary", "Short summary.", "md")["file"]
    second = texts.save_text(str(source), "summary", "Another one.", "md")["file"]
    assert first == str(tmp_path / "Lesson (summary).md")
    assert second == str(tmp_path / "Lesson (summary) (2).md")
    assert (tmp_path / "Lesson (summary).md").read_text(encoding="utf-8") == "Short summary.\n"


def test_long_texts_are_saved_in_parts(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("x")
    file = texts.save_text(str(source), "Kannada", "ಭಾಗ ಒಂದು", "txt")["file"]
    assert texts.save_text(str(source), "Kannada", "ಭಾಗ ಎರಡು\n", "txt", append_to=file)["file"] == file
    assert (tmp_path / "Lesson (Kannada).txt").read_text(encoding="utf-8") == "ಭಾಗ ಒಂದು\nಭಾಗ ಎರಡು\n"


def test_translated_segments_stay_a_segments_file_and_can_be_appended(tmp_path):
    source = tmp_path / "Lesson.segments.json"
    source.write_text("[]")
    part1 = json.dumps([{"start": 0.0, "end": 2.5, "text": "ನಮಸ್ಕಾರ"}], ensure_ascii=False)
    part2 = json.dumps([{"start": 2.5, "end": 4.0, "text": "ಧನ್ಯವಾದ"}], ensure_ascii=False)
    file = texts.save_text(str(source), "Kannada", part1, "json")["file"]
    assert file == str(tmp_path / "Lesson (Kannada).segments.json")
    texts.save_text(str(source), "Kannada", part2, "json", append_to=file)
    saved = json.loads((tmp_path / "Lesson (Kannada).segments.json").read_text(encoding="utf-8"))
    assert [s["text"] for s in saved] == ["ನಮಸ್ಕಾರ", "ಧನ್ಯವಾದ"]


def test_broken_segments_are_refused_with_a_plain_message(tmp_path):
    source = tmp_path / "Lesson.segments.json"
    source.write_text("[]")
    with pytest.raises(ToolError, match="list of"):
        texts.save_text(str(source), "Hindi", '[{"start": 0, "text": "no end"}]', "json")
    with pytest.raises(ToolError, match="isn't valid JSON"):
        texts.save_text(str(source), "Hindi", "[{", "json")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Lesson.segments.json"]


def test_appending_to_a_missing_file(tmp_path):
    with pytest.raises(ToolError, match="Save the first part"):
        texts.save_text(str(tmp_path / "a.txt"), "x", "y", "txt", append_to=str(tmp_path / "missing.txt"))
