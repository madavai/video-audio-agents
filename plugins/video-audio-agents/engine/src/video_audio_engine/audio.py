"""clean_audio: brings a recording to -16 LUFS, the loudness podcast apps and YouTube expect for speech, and cuts
the silence at its start and end. Two ffmpeg passes: the first measures, the second writes (a single pass misses
the loudness of short recordings by several LU).
mix_music: the person's own music under a narration, turned down by itself where the voice speaks, with their own
intro and outro. export_podcast: an mp3 at -16 LUFS with a title, cover picture and chapter markers."""
import datetime
import json
import math
import re

from mcp.server.mcpserver.exceptions import ToolError

from . import paths
from .clips import clock, has_audio, probe, probe_seconds, run, seconds
from .texts import existing

TARGET = "I=-16:TP=-1.5:LRA=11"  # -16 LUFS, peaks at most -1.5 dB
QUIET = "-45dB"  # quieter than this for half a second counts as silence
KEEP = 0.3  # seconds of the silence kept before the first sound and after the last
COUNT = "astats=measure_perchannel=none:measure_overall=Number_of_samples"  # the sound's length, as it is decoded
PODCAST = "I=-16:TP=-1.5:LRA=20"  # a mix of speech and music has a wider range than speech alone
STEREO = "aformat=sample_rates=44100:channel_layouts=stereo"  # what the mix is made in, whatever its files are


def clean_audio(job, file: str, loudness: bool = True, trim_silence: bool = True) -> dict:
    source = existing(file)
    if not (loudness or trim_silence):
        raise ToolError("Nothing to do: ask for the loudness, the silence trimmed, or both.")
    if not has_audio(source):
        raise ToolError(f"{source.name} has no sound to clean.")
    video = has_picture(source)
    length = probe_seconds(source)
    rate = probe(source, "-select_streams", "a:0", "-show_entries", "stream=sample_rate") or "48000"
    said, measured = measure(job, source, length, "Listening to the sound", end=50,
                             before=f"silencedetect=noise={QUIET}:d=0.5,{COUNT},")
    # The silence is found in the decoded sound, so its length is counted there too: a file's own length can be off
    # by a tenth of a second (found with an mp3 made on a Mac), and then the silence at the end wasn't seen as running
    # to the end, and was kept.
    counted = re.findall(r"Number of samples: (\d+)", said)
    length = int(counted[-1]) / int(rate) if counted else length

    first, last = 0.0, length
    if trim_silence and not video:  # cutting a video's sound would put its picture out of step
        starts = [float(t) for t in re.findall(r"silence_start: (-?[\d.]+)", said)]
        ends = [float(t) for t in re.findall(r"silence_end: ([\d.]+)", said)]
        silences = list(zip(starts, ends + [length]))  # a silence running to the end may have no end printed
        if silences and silences[0][0] <= 0.05:
            first = max(0.0, silences[0][1] - KEEP)
        if silences and silences[-1][1] >= length - 0.05:
            last = min(length, silences[-1][0] + KEEP)
        if last - first < 0.5:
            raise ToolError(f"{source.name} is silent from start to end.")
        if not loudness and first == 0 and last == length:
            raise ToolError(f"There is no silence to cut at the start or end of {source.name}; nothing was changed.")

    filters = [f"atrim={first:.3f}:{last:.3f},asetpts=PTS-STARTPTS"] if first > 0 or last < length else []
    if loudness:
        filters.append(normalise(measured))
    filters.append(f"aresample={rate}")  # loudnorm works at 192 kHz
    if video:  # the picture is copied as it is
        output = paths.free_path(source.parent, f"{source.stem} (clean audio)", ".mp4")
        args = ["-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart"]
    else:  # the same kind of file (an mp3 stays an mp3), without cover art
        output = paths.free_path(source.parent, f"{source.stem} (clean audio)", source.suffix.lower())
        args = ["-map", "0:a:0"]
    run(job, ["-i", str(source), *args, "-af", ",".join(filters), "-b:a", "192k"], output, last - first,
        "Writing the clean sound", start=50)
    return {"output_file": str(output), "seconds": round(last - first, 1),
            "silence_cut_seconds": round(length - (last - first), 1),
            "loudness_before": float(measured["input_i"])}


def mix_music(job, voice_file: str, music_file: str, music_volume: float = 0.4, intro_file: str | None = None,
              outro_file: str | None = None) -> dict:
    """The music under the voice, then the intro before it and the outro after it. Every file is first measured, so
    the levels follow the voice and not how loudly each file was made: the intro and outro play as loud as the voice,
    the music `music_volume` times as loud (1 = as loud, 0.4 = 8 dB quieter) where nobody speaks and, by itself,
    about 15 dB quieter again while the voice speaks (the sidechain's threshold sits 12 dB under the voice's loudness)."""
    voice, music = existing(voice_file), existing(music_file)
    extras = [(name, existing(file)) for name, file in (("intro", intro_file), ("outro", outro_file)) if file]
    if not 0.02 <= music_volume <= 1:
        raise ToolError("The music volume is between 0.02 (barely there) and 1 (as loud as the voice).")
    files = [voice, music, *(file for _, file in extras)]  # the order of ffmpeg's inputs
    for file in files:
        if not has_audio(file):
            raise ToolError(f"{file.name} has no sound.")
    length, loud = probe_seconds(voice), {}
    for i, file in enumerate(files):  # measuring takes the first 40% of the job
        if file not in loud:
            _, numbers = measure(job, file, probe_seconds(file), f"Listening to {file.name}", start=i * 40 / len(files),
                                 end=(i + 1) * 40 / len(files))
            loud[file] = float(numbers["input_i"])
    to_voice = [loud[voice] - loud[file] for file in files]  # the gain that makes each file as loud as the voice
    fade_in, fade_out = min(1, length / 4), min(2, length / 4)
    threshold = 10 ** ((loud[voice] - 12) / 20)
    graph = [f"[0:a]{STEREO},asplit=2[voice][heard]",
             f"[1:a]{STEREO},atrim=duration={length:.3f},volume={to_voice[1] + 20 * math.log10(music_volume):.2f}dB,"
             f"afade=t=in:d={fade_in:.2f},afade=t=out:st={length - fade_out:.3f}:d={fade_out:.2f}[bed]",
             f"[bed][heard]sidechaincompress=threshold={threshold:.5f}:ratio=20:attack=30:release=600:makeup=1[ducked]",
             "[voice][ducked]amix=inputs=2:duration=first:normalize=0[body]"]
    parts = ["[body]"]  # the intro goes before it, the outro after it
    for n, (name, _) in enumerate(extras, start=2):
        graph.append(f"[{n}:a]{STEREO},volume={to_voice[n]:.2f}dB[{name}]")
        parts = [f"[{name}]", *parts] if name == "intro" else [*parts, f"[{name}]"]
    graph.append(f"{''.join(parts)}concat=n={len(parts)}:v=0:a=1,alimiter=limit=0.97:level=0[mixed]")
    inputs = ["-i", str(voice), "-stream_loop", "-1", "-i", str(music)]  # a short piece of music is repeated
    for _, file in extras:
        inputs += ["-i", str(file)]
    total = length + sum(probe_seconds(file) for _, file in extras)
    output = paths.free_path(voice.parent, f"{voice.stem} (with music)", ".mp3")
    run(job, [*inputs, "-filter_complex", ";".join(graph), "-map", "[mixed]", "-c:a", "libmp3lame", "-b:a", "192k"],
        output, total, "Mixing the music under the voice", start=40)
    return {"output_file": str(output), "seconds": round(total, 1)}


def export_podcast(job, audio_file: str, chapters: str, title: str, artwork: str | None = None) -> dict:
    """An episode ready for podcast apps: an mp3 at -16 LUFS (two passes, like clean_audio), 128 kbps, with its title,
    a cover picture and the chapters from a chapters file written into the file (ID3 tags)."""
    source, title = existing(audio_file), title.strip()
    if not title:
        raise ToolError("Give the episode a title.")
    if not has_audio(source):
        raise ToolError(f"{source.name} has no sound to make an episode of.")
    length = probe_seconds(source)
    marks = chapter_marks(existing(chapters), length)
    cover = read_cover(existing(artwork)) if artwork else None
    _, measured = measure(job, source, length, "Listening to the sound", end=40)
    output = paths.free_path(source.parent, f"{source.stem} (podcast)", ".mp3")
    try:  # a file is only left when it has its tags: Stop or a failure in either step removes it
        run(job, ["-i", str(source), "-map", "0:a:0", "-map_metadata", "-1", "-map_chapters", "-1", "-af",
                  normalise(measured, PODCAST) + ",aresample=44100", "-c:a", "libmp3lame", "-b:a", "128k"],
            output, length, "Making the podcast file", start=40, end=98)
        write_tags(output, title, marks, length, cover)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {"output_file": str(output), "seconds": round(length, 1), "chapters": len(marks)}


def chapter_marks(file, length: float) -> list:
    """(start in seconds, title) for each line of a chapters file that begins with a time (1:30, 01:30 or 1:02:03):
    "00:00 Welcome", "- 02:30 - The first topic", "2. **05:10** Questions". Other lines (a heading) are skipped."""
    marks = []
    for line in file.read_text(encoding="utf-8").splitlines():
        found = re.match(r"^[\s\-*#>\[(]*(?:\d+[.)]\s+[*\[(]*)?(\d+(?::\d{1,2}){1,2})(?:\.\d+)?[\])*]*[\s\-–—:|]*(.*)$", line)
        if found:
            title = re.sub(r"[*_`#]+", "", found[2]).strip()
            marks.append((seconds(found[1]), title or f"Chapter {len(marks) + 1}"))
    if not marks:
        raise ToolError(f"There are no chapters in {file.name}: each line needs a time and a title, "
                        "like 02:30 The first topic.")
    marks.sort()
    for (start, name), (later, _) in zip(marks, marks[1:] + [(length, "")]):
        if start >= length:
            raise ToolError(f'The chapter "{name}" starts at {clock(start)}, but the audio is only {clock(length)} long. '
                            "Are the chapters from a transcript of this audio?")
        if later == start:
            raise ToolError(f'Two chapters start at {clock(start)}, "{name}" and the next one.')
    return marks


def read_cover(file) -> tuple:
    """(mime type, bytes) of a .jpg or .png picture, told by what is inside the file."""
    data = file.read_bytes()
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", data
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", data
    raise ToolError(f"{file.name} isn't a .jpg or .png picture.")


def write_tags(output, title: str, marks: list, length: float, cover) -> None:
    """The title, and the chapters and cover if there are any, as ID3 tags (version 2.3, which every player reads)."""
    from mutagen.id3 import APIC, CHAP, CTOC, ID3, TALB, TCON, TIT2, TYER, CTOCFlags
    text = dict(encoding=1)  # UTF-16, valid in 2.3 as well as 2.4, for any language
    tags = ID3()
    tags.add(TIT2(text=[title], **text))
    tags.add(TALB(text=[title], **text))
    tags.add(TCON(text=["Podcast"], **text))
    tags.add(TYER(text=[str(datetime.date.today().year)], **text))
    ends = [start for start, _ in marks[1:]] + [length]
    # mutagen writes the frames smallest first, which would put a chapter with a long title after the later ones in
    # the file (ffmpeg lists them in file order). Padding each chapter's name to the same size keeps them in order.
    size = [len(chapter.encode("utf-16")) for _, chapter in marks]
    names = [f"chp{i:03d}" + "_" * (max(size) - size[i]) for i in range(len(marks))]
    for name, (start, chapter), end in zip(names, marks, ends):
        tags.add(CHAP(element_id=name, start_time=round(start * 1000), end_time=round(end * 1000),
                      start_offset=0xFFFFFFFF, end_offset=0xFFFFFFFF, sub_frames=[TIT2(text=[chapter], **text)]))
    tags.add(CTOC(element_id="toc", flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED, child_element_ids=names,
                  sub_frames=[TIT2(text=[title], **text)]))
    if cover:
        tags.add(APIC(encoding=1, mime=cover[0], type=3, desc="Cover", data=cover[1]))
    tags.save(output, v1=0, v2_version=3)


def measure(job, source, length: float, label: str, start: float = 0, end: float = 100, before: str = "") -> tuple:
    """The measuring pass: ffmpeg's loudnorm numbers for the sound of `source`, after any filters in `before`
    (their messages, such as silencedetect's, come back too). Returns (messages, numbers)."""
    said = run(job, ["-i", str(source), "-map", "0:a:0", "-af", f"{before}loudnorm={TARGET}:print_format=json"],
               None, length, label, start=start, end=end)
    measured = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", said)[0])
    if measured["input_i"] == "-inf":
        raise ToolError(f"{source.name} is silent from start to end.")
    return said, measured


def normalise(measured: dict, target: str = TARGET) -> str:
    """The second pass's filter: the loudness set to the target from the numbers `measure` found."""
    return (f"loudnorm={target}:measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
            f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}:linear=true")


def has_picture(file) -> bool:
    """A video's picture; an mp3's cover art doesn't count."""
    return "video,0" in probe(file, "-select_streams", "v", "-show_entries",
                              "stream=codec_type:stream_disposition=attached_pic").splitlines()
