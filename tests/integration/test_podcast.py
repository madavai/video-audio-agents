"""mix_music and export_podcast on tones made by ffmpeg at test time: the voice is a 400 Hz tone that speaks for 2 s
and rests for 3 s, the music a 500 Hz tone, the intro 600 Hz and the outro 800 Hz, so each can be found in a mix."""
import json
import subprocess

import anyio
import numpy as np
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from mutagen.id3 import ID3

from video_audio_engine import audio, clips, models, progress, voices


def mix(voice, music, intro=None, outro=None, **options):
    """mix_music, with the music volume only when a test sets one (otherwise the default is used)"""
    return audio.mix_music(progress.Job(), str(voice), str(music), intro_file=intro and str(intro),
                           outro_file=outro and str(outro), **options)


def export(file, chapters, title="An episode", artwork=None):
    return audio.export_podcast(progress.Job(), str(file), str(chapters), title, artwork and str(artwork))


def tone_db(file, start, end, hertz):
    """How strong the tone at `hertz` is in seconds start to end of a file, in dB (a sine of amplitude 1 is 0 dB)."""
    samples = voices.read_audio(file, 44100)[int(start * 44100):int(end * 44100)]
    window = np.hanning(len(samples))
    spectrum = np.abs(np.fft.rfft(samples * window)) * 2 / window.sum()
    bin = round(hertz * len(samples) / 44100)
    return 20 * np.log10(spectrum[bin - 1:bin + 2].max() + 1e-9)


def loudest_tone(file, start, end):
    samples = voices.read_audio(file, 44100)[int(start * 44100):int(end * 44100)]
    spectrum = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return round(np.fft.rfftfreq(len(samples), 1 / 44100)[spectrum.argmax()])


@pytest.mark.parametrize("music", ["bed.mp3", "bed_loud.mp3"])
def test_the_music_turns_down_under_the_voice_whatever_its_own_loudness(copy_of, with_models, music):
    result = mix(copy_of("bursts.wav"), copy_of(music))  # 6 s of music under 15 s of voice: it is repeated
    out = result["output_file"]
    assert out.endswith("bursts (with music).mp3") and result["seconds"] == 15
    resting = tone_db(out, 3.8, 4.8, 500)  # the voice rests from 2 s to 5 s: the music is all there is
    speaking = tone_db(out, 5.8, 6.8, 500)  # the voice speaks from 5 s to 7 s
    assert resting - speaking > 10  # measurably lower under the voice
    # Where it rests the music plays at the default 0.4 (8 dB under) of the voice, however loud its own file was made.
    assert resting - tone_db(out, 5.8, 6.8, 400) == pytest.approx(-8, abs=3)
    assert tone_db(out, 10.8, 11.8, 500) < resting - 10  # and the third speaking (10 s to 12 s) has it down again


def test_the_music_fades_in_and_out_and_runs_the_whole_voice(copy_of, with_models):
    out = mix(copy_of("bursts.wav"), copy_of("bed.mp3"), music_volume=1)["output_file"]
    assert clips.probe_seconds(out) == pytest.approx(15, abs=0.1)
    assert tone_db(out, 2.2, 2.4, 500) > tone_db(out, 0.0, 0.2, 500) + 10  # faded in over the first second
    assert tone_db(out, 14.8, 15.0, 500) < tone_db(out, 3.0, 3.4, 500) - 10  # and out over the last two


def test_intro_and_outro_are_in_place_and_as_loud_as_the_voice(copy_of, with_models):
    result = mix(copy_of("bursts.wav"), copy_of("bed.mp3"), intro=copy_of("intro.mp3"), outro=copy_of("outro.mp3"))
    out = result["output_file"]
    # ffmpeg 7.0 (the Mac's) gives an mp3's length with its encoder's delay at the start: up to 0.08 s more.
    assert result["seconds"] == pytest.approx(19, abs=0.15) and clips.probe_seconds(out) == pytest.approx(19, abs=0.15)
    assert loudest_tone(out, 0.2, 1.8) == 600 and loudest_tone(out, 17.2, 18.8) == 800  # intro first, outro last
    assert loudest_tone(out, 2 + 5.8, 2 + 6.8) == 400  # the voice follows the intro; its words are not covered
    assert tone_db(out, 0.2, 1.8, 600) == pytest.approx(tone_db(out, 2 + 5.8, 2 + 6.8, 400), abs=2)
    assert tone_db(out, 17.2, 18.8, 800) == pytest.approx(tone_db(out, 2 + 5.8, 2 + 6.8, 400), abs=2)


def test_the_same_file_can_be_the_music_and_the_intro(copy_of, with_models):
    bed = copy_of("bed.mp3")
    result = mix(copy_of("bursts.wav"), bed, intro=bed)  # the music repeats without end; the intro must not
    assert result["seconds"] == pytest.approx(15 + 6, abs=0.1)  # the voice and one play of the 6 s of music
    assert clips.probe_seconds(result["output_file"]) == pytest.approx(15 + 6, abs=0.1)


def test_a_mix_is_never_overwritten(copy_of, with_models):
    voice, bed = copy_of("bursts.wav"), copy_of("bed.mp3")
    assert mix(voice, bed)["output_file"].endswith("bursts (with music).mp3")
    assert mix(voice, bed)["output_file"].endswith("bursts (with music) (2).mp3")


def test_mixing_asks_for_what_is_missing(copy_of, with_models, ffmpeg, tmp_path):
    voice, bed = copy_of("bursts.wav"), copy_of("bed.mp3")
    with pytest.raises(ToolError, match="There is no file"):
        mix(voice, tmp_path / "none.mp3")
    with pytest.raises(ToolError, match="music volume is between"):
        mix(voice, bed, music_volume=3)
    picture = voice.with_name("picture.mp4")
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=64x64:d=1", str(picture)], check=True)
    with pytest.raises(ToolError, match="picture.mp4 has no sound"):
        mix(voice, picture)
    hush = voice.with_name("hush.mp3")
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=duration=5", str(hush)], check=True)
    with pytest.raises(ToolError, match="hush.mp3 is silent"):
        mix(voice, hush)
    assert sorted(p.name for p in voice.parent.iterdir()) == ["bed.mp3", "bursts.wav", "hush.mp3", "picture.mp4"]


def test_stopping_a_mix_leaves_no_file(copy_of, with_models):
    voice, bed = copy_of("long.mp3"), copy_of("bed.mp3")  # long enough to be stopped part-way

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith("Mixing the music"):
                        scope.cancel()
            await progress.run(Ctx(), audio.mix_music, str(voice), str(bed), 0.25, None, None)

    anyio.run(main)
    assert sorted(p.name for p in voice.parent.iterdir()) == ["bed.mp3", "long.mp3"]


CHAPTERS = "# Chapters\n\n00:00 Welcome\n- 00:06 – The first topic, with a long title\n**00:12** Questions\n"


def chapters_file(folder, text=CHAPTERS):
    file = folder / "quiet (chapters).md"
    file.write_text(text, encoding="utf-8")
    return file


def png(ffmpeg, folder):
    cover = folder / "cover.png"
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "color=red:s=64x64", "-frames:v", "1",
                    str(cover)], check=True)
    return cover


def ffprobe(file):
    """What ffmpeg's own reader sees: the file's tags and chapters."""
    exe = str(models.ensure_ffmpeg() / ("ffprobe.exe" if clips.EXE else "ffprobe"))
    said = subprocess.run([exe, "-v", "error", "-show_chapters", "-show_format", "-of", "json", str(file)],
                          capture_output=True, text=True, encoding="utf-8").stdout
    return json.loads(said)


def test_the_episode_has_its_tags_and_chapters_readable_back(copy_of, with_models, ffmpeg):
    quiet = copy_of("quiet.mp3")  # 18 s, and quiet: about -27 LUFS
    cover = png(ffmpeg, quiet.parent)
    result = export(quiet, chapters_file(quiet.parent), "My first episode: Hello, world", cover)
    out = result["output_file"]
    assert out == str(quiet.with_name("quiet (podcast).mp3"))
    assert result["chapters"] == 3 and result["seconds"] == pytest.approx(18, abs=0.15)  # as above, on a Mac
    assert clips.probe_seconds(out) == pytest.approx(18, abs=0.15)

    tags = ID3(out)  # readable back with mutagen
    assert tags["TIT2"].text == ["My first episode: Hello, world"] and tags["TALB"].text == ["My first episode: Hello, world"]
    assert tags["TCON"].text == ["Podcast"]
    chapters = sorted(tags.getall("CHAP"), key=lambda chapter: chapter.start_time)
    assert [(c.start_time, c.sub_frames["TIT2"].text[0]) for c in chapters] == [
        (0, "Welcome"), (6000, "The first topic, with a long title"), (12000, "Questions")]
    assert [c.end_time for c in chapters[:2]] == [6000, 12000] and chapters[2].end_time == pytest.approx(18000, abs=100)
    assert tags["CTOC:toc"].child_element_ids == [c.element_id for c in chapters]
    picture = tags.getall("APIC")[0]
    assert picture.mime == "image/png" and picture.type == 3 and picture.data == cover.read_bytes()

    seen = ffprobe(out)  # and by ffmpeg's own reader, in the order they play
    assert seen["format"]["tags"]["title"] == "My first episode: Hello, world"
    assert [(float(c["start_time"]), c["tags"]["title"]) for c in seen["chapters"]] == [
        (0, "Welcome"), (6, "The first topic, with a long title"), (12, "Questions")]


def test_titles_in_other_scripts_survive(copy_of, with_models):
    quiet = copy_of("quiet.mp3")
    chapters = chapters_file(quiet.parent, "00:00 स्वागत\n00:09 ಪ್ರಶ್ನೆಗಳು\n")
    out = export(quiet, chapters, "हिंदी एपिसोड")["output_file"]
    assert ID3(out)["TIT2"].text == ["हिंदी एपिसोड"]
    seen = ffprobe(out)
    assert seen["format"]["tags"]["title"] == "हिंदी एपिसोड"
    assert [c["tags"]["title"] for c in seen["chapters"]] == ["स्वागत", "ಪ್ರಶ್ನೆಗಳು"]


def test_the_loudness_is_minus_16_within_one_unit(copy_of, with_models, meter):
    quiet = copy_of("quiet.mp3")
    assert meter(quiet) < -25
    out = export(quiet, chapters_file(quiet.parent), "Quiet one")["output_file"]
    assert meter(out) == pytest.approx(-16, abs=1)


def test_a_narration_with_music_exports_at_minus_16_too(copy_of, with_models, meter):
    mixed = mix(copy_of("bursts.wav"), copy_of("bed.mp3"), music_volume=0.5, intro=copy_of("intro.mp3"),
                outro=copy_of("outro.mp3"))["output_file"]
    chapters = chapters_file(copy_of("bed.mp3").parent, "00:00 Intro\n00:02 The talk\n00:17 Outro\n")
    result = export(mixed, chapters, "With music")
    assert meter(result["output_file"]) == pytest.approx(-16, abs=1)
    assert [c["tags"]["title"] for c in ffprobe(result["output_file"])["chapters"]] == ["Intro", "The talk", "Outro"]


def test_an_episode_without_a_cover_has_none_and_is_never_overwritten(copy_of, with_models):
    quiet = copy_of("quiet.mp3")
    chapters = chapters_file(quiet.parent)
    first = export(quiet, chapters, "One")["output_file"]
    assert ID3(first).getall("APIC") == []
    assert export(quiet, chapters, "One")["output_file"] == str(quiet.with_name("quiet (podcast) (2).mp3"))
    assert quiet.with_name("quiet (podcast).mp3").exists()


def test_a_source_with_its_own_tags_and_chapters_gives_only_the_new_ones(copy_of, with_models):
    quiet = copy_of("quiet.mp3")
    first = export(quiet, chapters_file(quiet.parent), "First")["output_file"]
    again = export(first, chapters_file(quiet.parent, "00:00 Only one\n"), "Second")["output_file"]
    assert [c["tags"]["title"] for c in ffprobe(again)["chapters"]] == ["Only one"]
    assert ID3(again)["TIT2"].text == ["Second"]


def test_export_says_what_is_wrong_before_doing_any_work(copy_of, with_models, tmp_path):
    quiet = copy_of("quiet.mp3")
    with pytest.raises(ToolError, match="Give the episode a title"):
        export(quiet, chapters_file(quiet.parent), "  ")
    with pytest.raises(ToolError, match="There are no chapters in quiet \\(chapters\\).md"):
        export(quiet, chapters_file(quiet.parent, "# Chapters\nNothing here\n"))
    with pytest.raises(ToolError, match='"Late" starts at 0:20, but the audio is only 0:18 long'):
        export(quiet, chapters_file(quiet.parent, "00:00 Start\n00:20 Late\n"))
    with pytest.raises(ToolError, match="Two chapters start at 0:05"):
        export(quiet, chapters_file(quiet.parent, "00:05 One\n00:05 Two\n"))
    notes = quiet.with_name("notes.txt")
    notes.write_text("not a picture", encoding="utf-8")
    good = chapters_file(quiet.parent)
    with pytest.raises(ToolError, match="notes.txt isn't a .jpg or .png picture"):
        export(quiet, good, "Title", notes)
    with pytest.raises(ToolError, match="There is no file"):
        export(quiet, tmp_path / "none.md", "Title")
    assert sorted(p.name for p in quiet.parent.iterdir()) == ["notes.txt", "quiet (chapters).md", "quiet.mp3"]


def test_stopping_an_export_leaves_no_file(copy_of, with_models):
    quiet = copy_of("long.mp3")  # 110 s: long enough to be stopped part-way
    chapters = chapters_file(quiet.parent)

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message.startswith("Making the podcast file"):
                        scope.cancel()
            await progress.run(Ctx(), audio.export_podcast, str(quiet), str(chapters), "Title", None)

    anyio.run(main)
    assert sorted(p.name for p in quiet.parent.iterdir()) == ["long.mp3", "quiet (chapters).md"]
