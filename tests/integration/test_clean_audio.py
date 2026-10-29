"""clean_audio on media made by ffmpeg at test time: loudness to -16 LUFS, silence cut at the start and end."""
import re
import subprocess

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import audio, clips, progress


def clean(file, loudness=True, trim_silence=True):
    return audio.clean_audio(progress.Job(), str(file), loudness, trim_silence)


def loudness(ffmpeg, file):
    """Integrated loudness in LUFS, measured by ffmpeg's EBU R128 meter."""
    said = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(file), "-af", "ebur128", "-f", "null", "-"],
                          capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", said)[-1])


def test_a_quiet_recording_is_brought_to_minus_16_and_its_silence_cut(copy_of, with_models, ffmpeg):
    quiet = copy_of("quiet.mp3")  # 3 s of near-silence, 11 s of speech, 4 s of near-silence
    assert loudness(ffmpeg, quiet) < -25
    result = clean(quiet)
    assert result["output_file"] == str(quiet.with_name("quiet (clean audio).mp3"))
    assert loudness(ffmpeg, result["output_file"]) == pytest.approx(-16, abs=1)
    assert result["loudness_before"] < -25 and result["silence_cut_seconds"] == pytest.approx(6.5, abs=0.3)
    assert clips.probe_seconds(result["output_file"]) == pytest.approx(result["seconds"], abs=0.1)


def test_never_overwritten(copy_of, with_models):
    quiet = copy_of("quiet.mp3")
    assert clean(quiet)["output_file"].endswith("quiet (clean audio).mp3")
    assert clean(quiet)["output_file"].endswith("quiet (clean audio) (2).mp3")


def test_only_the_silence_or_only_the_loudness(copy_of, with_models, ffmpeg):
    quiet = copy_of("quiet.mp3")
    trimmed = clean(quiet, loudness=False)["output_file"]
    assert clips.probe_seconds(trimmed) == pytest.approx(11.5, abs=0.3)
    assert loudness(ffmpeg, trimmed) == pytest.approx(loudness(ffmpeg, quiet), abs=1)
    louder = clean(quiet, trim_silence=False)
    assert louder["silence_cut_seconds"] == 0 and loudness(ffmpeg, louder["output_file"]) == pytest.approx(-16, abs=1)
    with pytest.raises(ToolError, match="Nothing to do"):
        clean(quiet, loudness=False, trim_silence=False)
    with pytest.raises(ToolError, match="no silence to cut"):
        clean(copy_of("talk.mp3"), loudness=False)


def test_a_video_keeps_its_picture_and_its_length(copy_of, with_models, ffmpeg):
    video = copy_of("narrated.mp4")  # music from the start, so nothing would be cut anyway
    result = clean(video)
    assert result["output_file"] == str(video.with_name("narrated (clean audio).mp4"))
    assert clips.has_video(result["output_file"]) and result["silence_cut_seconds"] == 0
    assert clips.probe_seconds(result["output_file"]) == pytest.approx(clips.probe_seconds(video), abs=0.1)
    assert loudness(ffmpeg, result["output_file"]) == pytest.approx(-16, abs=1)


def test_an_mp3_with_cover_art_stays_an_mp3(copy_of, with_models, ffmpeg):
    quiet = copy_of("quiet.mp3")
    cover, covered = quiet.with_name("cover.png"), quiet.with_name("covered.mp3")
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=64x64", "-frames:v", "1",
                    str(cover)], check=True)
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(quiet), "-i", str(cover), "-map", "0:a", "-map", "1:v",
                    "-c:a", "copy", "-c:v", "mjpeg", "-disposition:v", "attached_pic", str(covered)], check=True)
    assert clips.has_video(covered) and not audio.has_picture(covered)
    assert clean(covered)["output_file"].endswith("covered (clean audio).mp3")


def test_stopping_leaves_no_file(copy_of, with_models):
    long = copy_of("long.mp3")

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith("Writing the clean sound"):
                        scope.cancel()
            await progress.run(Ctx(), audio.clean_audio, str(long), True, True)

    anyio.run(main)
    assert [p.name for p in long.parent.iterdir()] == ["long.mp3"]


def test_files_without_sound(copy_of, with_models, ffmpeg, tmp_path):
    talk = copy_of("talk.mp4")
    silent = talk.with_name("silent.mp4")
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(talk), "-an", "-c", "copy", str(silent)], check=True)
    with pytest.raises(ToolError, match="no sound to clean"):
        clean(silent)
    hush = talk.with_name("hush.mp3")
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=duration=5", str(hush)], check=True)
    with pytest.raises(ToolError, match="silent from start to end"):
        clean(hush)
    with pytest.raises(ToolError, match="There is no file"):
        clean(tmp_path / "none.mp3")
