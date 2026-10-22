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


def thread(*lengths):
    return "\n\n".join(f"{n}/{len(lengths)} " + "a" * (size - len(f"{n}/{len(lengths)} "))
                       for n, size in enumerate(lengths, 1))


def test_x_posts_up_to_280_characters_are_saved(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("x")
    file = texts.save_text(str(source), "x-thread", thread(120, 280, 200), "txt")["file"]
    assert file == str(tmp_path / "Lesson (x-thread).txt")


def test_an_x_post_over_280_is_refused_by_number_and_nothing_is_saved(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("x")
    with pytest.raises(ToolError, match=r'X post 3 \("3/4 aaa.*"\) is 281 characters, over X.s limit of 280'):
        texts.save_text(str(source), "x-thread", thread(100, 100, 281, 100), "txt")
    with pytest.raises(ToolError, match="X post 1"):  # posts run together without blank lines
        texts.save_text(str(source), "X thread", thread(100, 100, 100).replace("\n\n", "\n"), "md")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Lesson.txt"]


def test_x_counts_emoji_and_chinese_as_two():
    assert texts.x_length("Hello — “world” ಕನ್ನಡ") == 21
    assert texts.x_length("🙂好") == 4


def test_titles_over_60_characters_are_refused(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("x")
    titles = "A" * 60 + "\n\n" + "B" * 61 + "\n"
    with pytest.raises(ToolError, match=r'Title 2 \("BBB.*"\) is 61 characters, over the 60 characters YouTube'):
        texts.save_text(str(source), "titles", titles, "txt")
    file = texts.save_text(str(source), "titles", titles.replace("B" * 61, "B" * 60), "txt")["file"]
    assert file == str(tmp_path / "Lesson (titles).txt")
    # Other drafts have no limit here.
    texts.save_text(str(source), "linkedin", "C" * 3000, "txt")


def test_added_titles_are_checked_too(tmp_path):
    source = tmp_path / "Lesson.txt"
    source.write_text("x")
    texts.save_text(str(source), "titles", "First", "txt")
    file = texts.save_text(str(source), "titles", "Second", "txt")["file"]
    assert file == str(tmp_path / "Lesson (titles) (2).txt")
    with pytest.raises(ToolError, match="Title 1"):
        texts.save_text(str(source), "", "D" * 61, "txt", append_to=file)
    texts.save_text(str(source), "", "Third", "txt", append_to=file)
    assert (tmp_path / "Lesson (titles) (2).txt").read_text(encoding="utf-8") == "Second\nThird\n"
