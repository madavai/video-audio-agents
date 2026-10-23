"""cut_clip and merge_audio_video on media made by ffmpeg at test time."""
import json
import subprocess
from pathlib import Path

import anyio
import numpy as np
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import clips, models, progress, subtitles, voices

FIXTURES = Path(__file__).parent.parent / "fixtures"


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


def level(audio):
    return 20 * np.log10(np.sqrt(np.mean(audio**2)) + 1e-9)


def test_a_dub_keeps_the_music_and_replaces_only_the_voice(copy_of, with_models):
    """The real music keeper (HTDemucs, 84 MB, kept in .test-data) on a video narrated over a tone and soft noise."""
    video, dub = copy_of("narrated.mp4"), copy_of("beep.mp3")
    lines = video.with_name("narrated (Hindi dubbing).segments.json")
    lines.write_text(json.dumps([{"start": 3.3, "end": 13.8, "text": "And so, my fellow Americans."},
                                 {"start": 15.0, "end": 15.5, "text": "…"}]), encoding="utf-8")  # no words: kept
    output = run(clips.merge_audio_video, str(video), str(dub), str(lines))["output_file"]
    assert output.endswith("narrated (new audio).mp4") and models.loaded.keys() == {"music"}
    assert clips.probe_seconds(output) == pytest.approx(clips.probe_seconds(video), abs=0.15)
    rate = 16000
    original, result = voices.read_audio(video, rate), voices.read_audio(output, rate)
    under = result - np.pad(voices.read_audio(dub, rate), (0, len(result)))[:len(result)]  # what plays under the dub
    speech = np.pad(voices.read_audio(FIXTURES / "jfk.wav", rate), (3 * rate, len(result)))[:len(result)]
    before, after, spoken = slice(0, int(2.4 * rate)), slice(int(14.7 * rate), None), slice(4 * rate, 13 * rate)
    for kept in (before, after):  # nobody speaks: the original sound, as it was
        assert level(result[kept] - original[kept]) < level(original[kept]) - 20
    assert np.corrcoef(original[spoken], speech[spoken])[0, 1] > 0.9
    assert np.corrcoef(under[spoken], speech[spoken])[0, 1] < 0.3  # the voice is gone...
    assert level(under[spoken]) == pytest.approx(level(original[before]), abs=3)  # ...and the music plays on


def test_a_dub_under_a_video_without_sound(copy_of, with_models, ffmpeg, monkeypatch):
    monkeypatch.setattr(models, "loaded", {})
    talk = copy_of("talk.mp4")
    video, dub = talk.with_name("silent.mp4"), copy_of("beep.mp3")
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(talk), "-an", "-c", "copy", str(video)], check=True)
    lines = video.with_name("lines.segments.json")
    lines.write_text(json.dumps([{"start": 0.0, "end": 5.0, "text": "Hello."}]), encoding="utf-8")
    output = run(clips.merge_audio_video, str(video), str(dub), str(lines))["output_file"]
    assert clips.probe_seconds(output) == pytest.approx(clips.probe_seconds(video), abs=0.15)
    assert "music" not in models.loaded  # nothing to keep, so no separating


def test_stopping_a_dub_while_keeping_its_music_leaves_no_file(copy_of, with_models):
    video, dub = copy_of("narrated.mp4"), copy_of("beep.mp3")
    lines = video.with_name("lines.segments.json")
    lines.write_text(json.dumps([{"start": 3.3, "end": 13.8, "text": "And so."}]), encoding="utf-8")
    before = sorted(p.name for p in video.parent.iterdir())

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith("Taking the voice out"):
                        scope.cancel()
            await progress.run(Ctx(), clips.merge_audio_video, str(video), str(dub), str(lines))

    anyio.run(main)
    assert sorted(p.name for p in video.parent.iterdir()) == before


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
