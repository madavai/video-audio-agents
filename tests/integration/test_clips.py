"""cut_clip and merge_audio_video on media made by ffmpeg at test time."""
import subprocess

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import clips, progress, subtitles


def run(work, *args):
    return work(progress.Job(), *args)


def test_times(with_models):
    assert clips.seconds("01:30") == 90 and clips.seconds("1:02:03") == 3723 and clips.seconds("90.5") == 90.5
    assert clips.seconds(45) == 45 and clips.clock(90) == "1:30" and clips.clock(3723, "-") == "1-02-03"
    with pytest.raises(ToolError, match="isn't a time"):
        clips.seconds("one minute")


def test_clip_without_captions_is_copied(copy_of, with_models):
    video = copy_of("long.mp4")
    clip = run(clips.cut_clip, str(video), "01:00", "01:30")["clip_file"]
    assert clip.endswith("long (clip 1-00 to 1-30).mp4")
    assert clips.probe_seconds(clip) == pytest.approx(30, abs=2.5)  # starts at the keyframe before 1:00


def test_a_video_with_a_timecode_track_is_cut(copy_of, with_models, ffmpeg):
    """Professional exports carry a timecode track that an mp4 can't take when copied (found on a NASA video)."""
    video = copy_of("long.mp4")
    stamped = video.with_name("stamped.mp4")
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(video), "-map", "0", "-c", "copy", "-timecode",
                    "00:00:00:00", str(stamped)], check=True)
    assert "data" in clips.probe(stamped, "-show_entries", "stream=codec_type")
    clip = run(clips.cut_clip, str(stamped), "0:10", "0:20")["clip_file"]
    assert clips.probe_seconds(clip) == pytest.approx(10, abs=2.5) and clips.has_video(clip)


def test_clip_with_captions_burned_in(copy_of, with_models):
    video = copy_of("long.mp4")
    srt = video.parent / "long.srt"
    srt.write_text(subtitles.write(subtitles.to_cues(
        [{"start": 58, "end": 64, "text": "And so, my fellow Americans, ask not."}]), "srt"), encoding="utf-8")
    clip = run(clips.cut_clip, str(video), "60", "70", str(srt))["clip_file"]
    assert clip.endswith("long (clip 1-00 to 1-10) (captions).mp4")
    assert clips.probe_seconds(clip) == pytest.approx(10, abs=0.2)  # re-encoded, so exact
    assert clips.has_video(clip)


def test_an_audio_clip_and_times_past_the_end(copy_of, with_models):
    audio = copy_of("long.mp3")
    clip = run(clips.cut_clip, str(audio), "100", "500")["clip_file"]
    assert clip.endswith(".mp3") and clips.probe_seconds(clip) == pytest.approx(10, abs=1)
    with pytest.raises(ToolError, match="only 1:50 long"):
        run(clips.cut_clip, str(audio), "3:00", "3:30")
    with pytest.raises(ToolError, match="no picture"):
        run(clips.cut_clip, str(audio), "0", "5", str(audio))


def test_new_audio_under_a_video_keeps_the_video_length(copy_of, with_models):
    video, short_audio, long_audio = copy_of("talk.mp4"), copy_of("talk.mp3"), copy_of("long.mp3")
    dubbed = short_audio.with_name("talk (Hindi).mp3")
    short_audio.rename(dubbed)
    first = run(clips.merge_audio_video, str(video), str(dubbed))["output_file"]
    assert first.endswith("talk (Hindi).mp4")
    second = run(clips.merge_audio_video, str(video), str(long_audio))["output_file"]
    assert second.endswith("talk (new audio).mp4")
    for output in (first, second):
        assert clips.probe_seconds(output) == pytest.approx(clips.probe_seconds(video), abs=0.15)


def test_stopping_a_captioned_clip_leaves_no_file(copy_of, with_models):
    video = copy_of("long.mp4")
    srt = video.parent / "long.srt"
    srt.write_text(subtitles.write([(0, 100, ["Caption"])], "srt"), encoding="utf-8")

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if "%" in message:
                        scope.cancel()
            await progress.run(Ctx(), clips.cut_clip, str(video), "0", "110", str(srt))

    anyio.run(main)
    assert sorted(p.name for p in video.parent.iterdir()) == ["long.mp4", "long.srt"]


def test_a_missing_file(tmp_path, with_models):
    with pytest.raises(ToolError, match="There is no file"):
        run(clips.cut_clip, str(tmp_path / "none.mp4"), "0", "5")
