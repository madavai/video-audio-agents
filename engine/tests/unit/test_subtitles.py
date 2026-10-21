import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import subtitles

LONG = ("So today we are going to look at how a transcript turns into subtitles that people can actually read "
        "on a phone screen, without the lines running off the edge or flashing past too quickly.")


def check(cues, max_chars=42):
    for start, end, lines in cues:
        assert 1 <= len(lines) <= 2 and all(len(line) <= max_chars for line in lines), lines
        assert 0 < end - start <= subtitles.MAX_SECONDS + 0.01
    assert all(a[1] <= b[0] + 1e-6 for a, b in zip(cues, cues[1:]))  # in order, never overlapping


def test_a_long_sentence_is_split_into_readable_captions():
    cues = subtitles.to_cues([{"start": 0, "end": 10, "text": LONG}])
    check(cues)
    assert len(cues) >= 3
    assert " ".join(" ".join(lines) for _, _, lines in cues) == LONG  # no word lost or changed
    assert cues[0][0] == 0 and cues[-1][1] == pytest.approx(10)


def test_a_slow_short_line_is_split_to_stay_under_six_seconds():
    cues = subtitles.to_cues([{"start": 5, "end": 20, "text": "Well. Hmm. Let me think about that."}])
    check(cues)
    assert len(cues) >= 3


def test_translated_text_and_a_narrower_width():
    text = "ಇಂದು ನಾವು ಉಪಶೀರ್ಷಿಕೆಗಳನ್ನು ಹೇಗೆ ಮಾಡುವುದು ಎಂದು ನೋಡೋಣ ಮತ್ತು ಅವುಗಳನ್ನು ಓದಲು ಸುಲಭವಾಗಿಸೋಣ"
    cues = subtitles.to_cues([{"start": 0, "end": 5, "text": text}], max_chars=30)
    check(cues, 30)


def test_a_very_long_word_is_cut_rather_than_overflowing():
    cues = subtitles.to_cues([{"start": 0, "end": 4, "text": "x" * 120}])
    check(cues)


def test_overlapping_segments_are_kept_in_order():
    cues = subtitles.to_cues([{"start": 0, "end": 3, "text": "First line."},
                              {"start": 2.5, "end": 4, "text": "Second line."}])
    check(cues)


def test_srt_and_vtt_files(tmp_path):
    source = tmp_path / "Lesson (Kannada).segments.json"
    source.write_text(json.dumps([{"start": 1.5, "end": 3.25, "text": "ನಮಸ್ಕಾರ"},
                                  {"start": 3661, "end": 3663, "text": "Later"}], ensure_ascii=False),
                      encoding="utf-8")
    srt = subtitles.make_subtitles(str(source), "srt")
    assert srt == {"subtitle_file": str(tmp_path / "Lesson (Kannada).srt"), "cues": 2}
    assert (tmp_path / "Lesson (Kannada).srt").read_text(encoding="utf-8") == (
        "1\n00:00:01,500 --> 00:00:03,250\nನಮಸ್ಕಾರ\n\n2\n01:01:01,000 --> 01:01:03,000\nLater\n\n")
    vtt = (tmp_path / "Lesson (Kannada).vtt")
    subtitles.make_subtitles(str(source), "vtt")
    assert vtt.read_text(encoding="utf-8").startswith("WEBVTT\n\n00:00:01.500 --> 00:00:03.250\nನಮಸ್ಕಾರ\n")
    assert subtitles.make_subtitles(str(source), "srt")["subtitle_file"].endswith("Lesson (Kannada) (2).srt")


def test_reading_back_and_shifting_to_a_clip(tmp_path):
    cues = subtitles.to_cues([{"start": 55, "end": 62, "text": LONG}, {"start": 95, "end": 99, "text": "Late."}])
    path = tmp_path / "a.srt"
    path.write_text(subtitles.write(cues, "srt"), encoding="utf-8")
    back = subtitles.read(path)
    assert [lines for _, _, lines in back] == [lines for _, _, lines in cues]
    assert back[0][0] == pytest.approx(55)
    shifted = subtitles.window(back, 60, 90)
    assert shifted[0][0] == 0 and all(0 <= a < b <= 30 for a, b, _ in shifted)
    assert "Late." not in [line for _, _, lines in shifted for line in lines]
    vtt = tmp_path / "a.vtt"
    vtt.write_text("WEBVTT\n\n01:02.500 --> 01:04.000 align:start\nShort form\n", encoding="utf-8")
    assert subtitles.read(vtt) == [(62.5, 64.0, ["Short form"])]


def test_a_broken_segments_file(tmp_path):
    source = tmp_path / "x.segments.json"
    source.write_text('[{"start": 0}]')
    with pytest.raises(ToolError, match="list of"):
        subtitles.make_subtitles(str(source))
