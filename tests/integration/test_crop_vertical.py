"""crop_vertical on a wide video in three bands (red | green | blue) made by ffmpeg at test time."""
import subprocess

import anyio
import numpy as np
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import clips, progress, subtitles

WIDE_CAPTION = ["And so, my fellow Americans, ask not what", "your country can do for you, ask what you"]  # 41 each


def run(work, *args):
    return work(progress.Job(), *args)


def size(file):
    return clips.probe(file, "-select_streams", "v", "-show_entries", "stream=width,height")


def frame(ffmpeg, file, at):
    """The picture at `at` seconds, as rows x columns x (red, green, blue)."""
    raw = subprocess.run([ffmpeg, "-loglevel", "error", "-ss", str(at), "-i", str(file), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)


def test_the_whole_video_made_upright_keeps_the_middle(copy_of, with_models, ffmpeg):
    video = copy_of("thirds.mp4")
    output = run(clips.crop_vertical, str(video))["output_file"]
    assert output.endswith("thirds (vertical).mp4")
    assert size(output) == "1080,1920"
    assert clips.probe_seconds(output) == pytest.approx(clips.probe_seconds(video), abs=0.1)
    assert clips.has_audio(output)
    red, green, blue = frame(ffmpeg, output, 1).reshape(-1, 3).mean(axis=0)
    assert green > 100 and red < 20 and blue < 20  # only the middle band


@pytest.mark.parametrize("focus, band", [("left", 0), ("right", 2)])
def test_focus_keeps_the_left_or_right_side(copy_of, with_models, ffmpeg, focus, band):
    video = copy_of("thirds.mp4")
    output = run(clips.crop_vertical, str(video), focus)["output_file"]
    colour = frame(ffmpeg, output, 1).reshape(-1, 3).mean(axis=0)
    assert colour.argmax() == band and colour[band] > 200 and np.delete(colour, band).max() < 20


def test_a_part_starts_exactly_and_nothing_is_overwritten(copy_of, with_models):
    video = copy_of("thirds.mp4")
    first = run(clips.crop_vertical, str(video), "center", "0:01", "0:04")["output_file"]
    second = run(clips.crop_vertical, str(video), "center", "1", "4")["output_file"]
    assert first.endswith("thirds (vertical 0-01 to 0-04).mp4")
    assert second.endswith("thirds (vertical 0-01 to 0-04) (2).mp4")
    assert clips.probe_seconds(first) == pytest.approx(3, abs=0.1)


def test_an_upright_video_stays_upright(copy_of, with_models, ffmpeg):
    wide = copy_of("thirds.mp4")
    upright = wide.with_name("upright.mp4")
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(wide), "-vf", "crop=404:720,scale=720:1280",
                    "-c:a", "copy", str(upright)], check=True)
    output = run(clips.crop_vertical, str(upright), "left")["output_file"]
    assert size(output) == "1080,1920"
    assert frame(ffmpeg, output, 1).reshape(-1, 3).mean(axis=0)[1] > 100  # all of it kept: still green


def test_captions_are_burned_in_whole_after_the_crop(copy_of, with_models, ffmpeg):
    """A caption written for the wide picture (2 lines of 42 characters) would lose both ends in a 9:16 crop;
    here it is cut into short lines that fit, well inside the sides of the upright picture."""
    video = copy_of("thirds.mp4")
    srt = video.with_name("thirds.srt")
    srt.write_text(subtitles.write([(0, 7, WIDE_CAPTION)], "srt"), encoding="utf-8")
    output = run(clips.crop_vertical, str(video), "center", "0", "6", str(srt))["output_file"]
    assert output.endswith("thirds (vertical 0-00 to 0-06) (captions).mp4")
    assert size(output) == "1080,1920"
    for at in (1, 5):  # the caption's two pieces: "And so, ... ask not what", "your country ... what you"
        white = frame(ffmpeg, output, at).min(axis=2) > 200  # letters are white; the bands never are
        rows, columns = np.nonzero(white)
        assert len(rows) > 2000  # a caption is there...
        assert columns.min() > 80 and columns.max() < 1000  # ...whole, clear of both sides
        assert 1000 < rows.min() and rows.max() < 1920 - 400  # above the apps' title and buttons


def test_subtitles_of_another_video_are_refused(copy_of, with_models):
    video = copy_of("thirds.mp4")
    srt = video.with_name("other.srt")
    srt.write_text(subtitles.write([(60, 65, ["Somewhere else"])], "srt"), encoding="utf-8")
    with pytest.raises(ToolError, match="no captions between 0:00 and 0:08"):
        run(clips.crop_vertical, str(video), "center", None, None, str(srt))
    assert sorted(p.name for p in video.parent.iterdir()) == ["other.srt", "thirds.mp4"]


def test_a_recording_without_a_picture(copy_of, with_models):
    with pytest.raises(ToolError, match="has no picture"):
        run(clips.crop_vertical, str(copy_of("talk.mp3")))


def test_stopping_leaves_no_file(copy_of, with_models):
    video = copy_of("long.mp4")

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if "%" in message:
                        scope.cancel()
            await progress.run(Ctx(), clips.crop_vertical, str(video))

    anyio.run(main)
    assert sorted(p.name for p in video.parent.iterdir()) == ["long.mp4"]


def test_the_whole_picture_on_a_blurred_copy_keeps_all_of_it(copy_of, with_models, ffmpeg):
    """For interviews framed to one side, two people, or text on screen: nothing is cut off."""
    video = copy_of("thirds.mp4")
    output = run(clips.crop_vertical, str(video), "whole")["output_file"]
    assert size(output) == "1080,1920"
    middle = frame(ffmpeg, output, 1)[960]  # the picture fills the width across the middle: all three bands
    assert middle[60].argmax() == 0 and middle[540].argmax() == 1 and middle[1020].argmax() == 2
