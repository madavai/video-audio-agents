"""translated_segments, the glossary, and a 1-hour transcript translated in parts without losing a line."""
import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import paths, subtitles, texts, transcribe


def lesson(folder, count, seconds_each=4.0):
    """A transcript like transcribe makes: <name>.txt with "[12.5s] text" lines and <name>.segments.json."""
    segments = [{"start": round(i * seconds_each, 2), "end": round(i * seconds_each + 3.5, 2),
                 "text": f"Sentence number {i}."} for i in range(count)]
    (folder / "Lesson.segments.json").write_text(json.dumps(segments), encoding="utf-8")
    (folder / "Lesson.txt").write_text(transcribe.as_text(segments, True), encoding="utf-8")
    return segments


def translate(line):
    """Stands in for the AI: '[4.0s] Sentence number 1.' -> '[4.0s] ವಾಕ್ಯ ಸಂಖ್ಯೆ 1.'"""
    stamp, text = line.split("] ", 1)
    return f"{stamp}] ವಾಕ್ಯ ಸಂಖ್ಯೆ {text.split()[-1]}"


def test_a_one_hour_transcript_translated_in_parts_loses_nothing(tmp_path):
    segments = lesson(tmp_path, 900)  # one line every 4 seconds for an hour
    lines = (tmp_path / "Lesson.txt").read_text(encoding="utf-8").splitlines()
    file = None
    for start in range(0, len(lines), 150):  # how the translator works: parts of about 150 lines
        part = "\n".join(translate(line) for line in lines[start:start + 150])
        file = texts.save_text(str(tmp_path / "Lesson.txt"), "Kannada", part, "txt", append_to=file)["file"]
    assert file == str(tmp_path / "Lesson (Kannada).txt")
    result = texts.translated_segments(str(tmp_path / "Lesson.segments.json"), file)
    assert result == {"segments_file": str(tmp_path / "Lesson (Kannada).segments.json"), "lines": 900}
    translated = json.loads((tmp_path / "Lesson (Kannada).segments.json").read_text(encoding="utf-8"))
    assert [(s["start"], s["end"]) for s in translated] == [(s["start"], s["end"]) for s in segments]
    assert translated[899]["text"] == "ವಾಕ್ಯ ಸಂಖ್ಯೆ 899."
    srt = subtitles.make_subtitles(result["segments_file"])["subtitle_file"]
    assert srt.endswith("Lesson (Kannada).srt") and "ವಾಕ್ಯ ಸಂಖ್ಯೆ 899." in open(srt, encoding="utf-8").read()


def test_missing_lines_are_named_then_can_be_added_at_the_end(tmp_path):
    lesson(tmp_path, 20)
    lines = (tmp_path / "Lesson.txt").read_text(encoding="utf-8").splitlines()
    skipped = [lines[7], lines[12]]
    kept = [translate(line) for line in lines if line not in skipped]
    file = texts.save_text(str(tmp_path / "Lesson.txt"), "Kannada", "\n".join(kept), "txt")["file"]
    with pytest.raises(ToolError, match=r"2 line\(s\) missing: \[28.0s\], \[48.0s\]"):
        texts.translated_segments(str(tmp_path / "Lesson.segments.json"), file)
    texts.save_text(file, "", "\n".join(translate(line) for line in skipped), "txt", append_to=file)
    texts.translated_segments(str(tmp_path / "Lesson.segments.json"), file)
    fixed = (tmp_path / "Lesson (Kannada).txt").read_text(encoding="utf-8").splitlines()
    assert fixed == [translate(line) for line in lines]  # put back in order


def test_unknown_times_merged_lines_and_wrapped_lines(tmp_path):
    lesson(tmp_path, 3)
    translated = tmp_path / "Lesson (Hindi).txt"
    translated.write_text("Hindi translation\n[0.0s] वाक्य\nजारी\n[4.0s] दो\n[8.0s]\n[9.9s] अतिरिक्त\n", encoding="utf-8")
    with pytest.raises(ToolError) as error:
        texts.translated_segments(str(tmp_path / "Lesson.segments.json"), str(translated))
    assert "1 line(s) missing: [8.0s]" in str(error.value)  # a time with no words counts as missing
    assert "[9.9s]" in str(error.value)
    translated.write_text("[0.0s] वाक्य\nजारी\n[4.0s] दो\n[8.0s] तीन\n", encoding="utf-8")
    result = texts.translated_segments(str(tmp_path / "Lesson.segments.json"), str(translated))
    saved = json.loads(open(result["segments_file"], encoding="utf-8").read())
    assert [s["text"] for s in saved] == ["वाक्य जारी", "दो", "तीन"]  # a wrapped line joins the line before


def test_a_translation_without_times(tmp_path):
    lesson(tmp_path, 2)
    plain = tmp_path / "Lesson (French).txt"
    plain.write_text("Phrase un.\n\nPhrase deux.\n", encoding="utf-8")
    with pytest.raises(ToolError, match="no \"\\[12.5s\\] text\" lines"):
        texts.translated_segments(str(tmp_path / "Lesson.segments.json"), str(plain))


def test_glossary_is_created_in_the_output_folder_then_added_to(tmp_path):
    glossary = paths.output_root() / "glossary.md"
    assert not paths.output_root().exists()
    file = texts.save_text(str(glossary), "", "process map → keep in English", "md")["file"]
    assert file == str(glossary)
    texts.save_text(str(glossary), "", "Madav → ಮಾಧವ್", "md", append_to=file)
    assert glossary.read_text(encoding="utf-8") == "process map → keep in English\nMadav → ಮಾಧವ್\n"


def test_folders_outside_the_output_folder_are_not_created(tmp_path):
    with pytest.raises(ToolError, match="doesn't exist"):
        texts.save_text(str(tmp_path / "nowhere" / "a.txt"), "x", "y", "txt")
