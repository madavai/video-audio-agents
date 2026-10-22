"""transcribe with the fast model on the 11-second public-domain speech sample (tests/fixtures/jfk.wav)."""
import json
import subprocess
from pathlib import Path

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import progress, transcribe

WORDS = ["ask not", "country"]
FIXTURES = Path(__file__).parent.parent / "fixtures"


def run(file, **kwargs):
    return transcribe.transcribe(progress.Job(), str(file), accuracy="fast", **kwargs)


def test_mp3_with_timestamps(copy_of, with_models):
    audio = copy_of("talk.mp3")
    result = run(audio)
    text = (audio.parent / "talk.txt").read_text(encoding="utf-8")
    assert result["transcript_file"] == str(audio.parent / "talk.txt")
    assert result["language"] == "en" and 10 < result["duration_seconds"] < 12
    assert all(word in text.lower() for word in WORDS)
    assert text.startswith("[0.")
    segments = json.loads((audio.parent / "talk.segments.json").read_text(encoding="utf-8"))
    assert len(segments) == result["lines"] and set(segments[0]) == {"start", "end", "text"}
    assert all(a["start"] <= b["start"] for a, b in zip(segments, segments[1:]))


def test_mp4_as_paragraphs(copy_of, with_models):
    video = copy_of("talk.mp4")
    result = run(video, timestamps=False)
    text = (video.parent / "talk.txt").read_text(encoding="utf-8")
    assert "[" not in text and all(word in text.lower() for word in WORDS)
    assert result["segments_file"].endswith("talk.segments.json")


def test_a_second_transcript_gets_its_own_name(copy_of, with_models):
    audio = copy_of("talk.mp3")
    run(audio)
    second = run(audio)
    assert second["transcript_file"].endswith("talk (2).txt")
    assert second["segments_file"].endswith("talk (2).segments.json")


def test_delete_audio_after_removes_audio_but_never_a_video(copy_of, with_models):
    audio, video = copy_of("talk.mp3"), copy_of("talk.mp4")
    run(audio, delete_audio_after=True)
    run(video, delete_audio_after=True)
    assert not audio.exists() and video.exists()


def test_stopping_leaves_no_half_written_transcript(copy_of, with_models):
    audio = copy_of("long.mp3")

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith(("Listening", "Transcribing")):
                        scope.cancel()
            await progress.run(Ctx(), transcribe.transcribe, str(audio), "fast", True, False)

    anyio.run(main)
    assert sorted(p.name for p in audio.parent.iterdir()) == ["long.mp3"]


@pytest.mark.slow
def test_a_long_recording_with_the_balanced_model(tmp_path, ffmpeg, with_models):
    """Ten minutes fill whole batches of 8, which crashed the engine on a 24-core PC when it used 12 threads.
    Downloads the balanced model (0.5 GB) into the shared test folder the first time."""
    audio = tmp_path / "ten minutes.mp3"
    subprocess.run([ffmpeg, "-loglevel", "error", "-stream_loop", "54", "-i", str(FIXTURES / "jfk.wav"), str(audio)],
                   check=True)
    result = transcribe.transcribe(progress.Job(), str(audio), "balanced")
    assert result["duration_seconds"] > 600 and result["lines"] > 50


def test_not_a_media_file(tmp_path, with_models):
    fake = tmp_path / "notes.mp3"
    fake.write_text("not audio")
    with pytest.raises(ToolError, match="couldn't be read"):
        run(fake)


def test_missing_file(tmp_path):
    with pytest.raises(ToolError, match="There is no file"):
        run(tmp_path / "nothing.mp3")


def test_lines_end_at_sentences_pauses_and_twelve_seconds():
    from types import SimpleNamespace as W
    words = [W(word=" Hello", start=0.0, end=0.5), W(word=" there.", start=0.5, end=2.0),  # sentence end
             W(word=" After", start=2.1, end=2.5), W(word=" a", start=2.5, end=2.6),
             W(word=" pause", start=4.0, end=4.5)]  # 1.4 s gap
    words += [W(word=f" w{i}", start=5.0 + i, end=5.9 + i) for i in range(14)]  # runs past 12 seconds
    lines = transcribe.to_lines([W(words=words, end=19.0)], 19.0, progress.Job())
    assert [line["text"] for line in lines][:3] == ["Hello there.", "After a", "pause w0 w1 w2 w3 w4 w5 w6 w7 w8 w9 w10"]
    assert lines[0] == {"start": 0.0, "end": 2.0, "text": "Hello there."}
    assert all(line["end"] - line["start"] <= 12 for line in lines)


def test_paragraphs_break_after_long_sentences():
    lines = [{"start": i, "end": i + 1, "text": "word " * 50 + "end."} for i in range(4)]
    text = transcribe.as_text(lines, timestamps=False)
    assert text.count("\n\n") == 1 and text.endswith("end.\n")
