"""The engine: an MCP server whose tools the four agents call. Tool definitions only; the work is in the modules."""
import argparse
import json
import logging
import logging.handlers
import os
import sys

from typing import Literal

from mcp.server.mcpserver import Context, MCPServer

from . import clips, media, models, progress, setup_check, speech, subtitles, texts, voices
from . import transcribe as speech_to_text
from .paths import data_dir

mcp = MCPServer(
    "engine",
    instructions="Downloads, transcribes, subtitles, cuts, voices and dubs video and audio. "
    "Every tool returns a small JSON object; files are never overwritten.",
)


@mcp.tool()
def check_setup() -> str:
    """What is installed and what is missing: Python, ffmpeg, Deno, a browser for login pages, which models are
    downloaded and how many GB each missing one needs, free memory and disk. Fast; downloads nothing.
    Call it once before heavy work."""
    return json.dumps(setup_check.check_setup())


@mcp.tool()
async def fetch_media(url: str, save: Literal["audio", "video", "both"], ctx: Context, folder: str | None = None) -> str:
    """Downloads one link: save="audio" gives an .mp3, "video" an .mp4, "both" both. Works for YouTube and most
    video sites, direct file links, and pages behind a login (it opens the page in Edge or Chrome; the person may
    need to log in there the first time). Files go into Documents/VideoAudioAgents/<title>/, or <folder>/<title>/.
    Returns {title, folder, files, used_browser}. One link per call."""
    return json.dumps(await progress.run(ctx, media.fetch_media, url, save, folder))


@mcp.tool()
async def transcribe(file: str, ctx: Context, accuracy: Literal["fast", "balanced", "accurate"] = "balanced",
                     timestamps: bool = True, delete_audio_after: bool = False) -> str:
    """Speech to text for an audio or video file. Writes <name>.txt next to it (one "[12.5s] text" line per
    segment with timestamps, otherwise paragraphs) and <name>.segments.json (start, end, text), which subtitles,
    clips and dubbing are made from. accuracy: fast, balanced (default) or accurate (slower; downloads 1.5 GB
    the first time). delete_audio_after removes the audio file afterwards (never a video).
    Returns {transcript_file, segments_file, language, lines, duration_seconds}."""
    return json.dumps(await progress.run(ctx, speech_to_text.transcribe, file, accuracy, timestamps,
                                         delete_audio_after))


@mcp.tool()
def save_text(next_to: str, label: str, text: str, ext: Literal["txt", "md", "srt", "json"] = "txt",
              append_to: str | None = None) -> str:
    """Saves text you wrote (a translation, summary, chapters, notes, a post) as "<name> (<label>).ext" next to
    the file `next_to`, never overwriting. With an empty label it is saved under next_to's own name (for example
    <output_folder>/glossary.md). For long texts, save the first part, then pass the returned path as append_to
    for each later part. JSON next to a .segments.json file is saved as "<name> (<label>).segments.json" and
    must be a list of {start, end, text}; appending extends the list. Drafts with a length limit are refused,
    naming the piece to shorten: label "titles" (one per line, each at most 60 characters) and label "x-thread"
    (a blank line between posts, each at most 280 characters as X counts them). Returns {file}."""
    try:
        return json.dumps(texts.save_text(next_to, label, text, ext, append_to))
    except Exception as e:
        raise progress.plain_error(e) from e


@mcp.tool()
def translated_segments(segments_file: str, translated_file: str) -> str:
    """For translated subtitles and dubbing: pairs a translated transcript, written as "[12.5s] text" lines (one
    per original line, times kept), with the original .segments.json. Saves "<translated name>.segments.json"
    with the original times and the translated words. Fails with the list of missing or unknown times if the
    translation isn't complete line for line, so nothing is lost. Returns {segments_file, lines}."""
    try:
        return json.dumps(texts.translated_segments(segments_file, translated_file))
    except Exception as e:
        raise progress.plain_error(e) from e


@mcp.tool()
def make_subtitles(segments_file: str, format: Literal["srt", "vtt"] = "srt", max_chars: int = 42) -> str:
    """Subtitles (.srt, or .vtt for the web) from a .segments.json file: the original or a translated one.
    At most 2 lines of max_chars characters and 6 seconds per caption. Saved next to the segments file.
    Returns {subtitle_file, cues}."""
    try:
        return json.dumps(subtitles.make_subtitles(segments_file, format, max_chars))
    except Exception as e:
        raise progress.plain_error(e) from e


@mcp.tool()
async def cut_clip(video_file: str, start: str, end: str, ctx: Context, subtitle_file: str | None = None) -> str:
    """Cuts the part between start and end (minutes:seconds like "01:30", or seconds like "90") out of a video
    or audio file, saved next to it. Without subtitle_file it is copied as is (instant; the start may move
    back a second or two to the nearest keyframe). With subtitle_file (.srt or .vtt of the same video) the
    captions are burned into the picture (slower; exact start). Returns {clip_file}."""
    return json.dumps(await progress.run(ctx, clips.cut_clip, video_file, start, end, subtitle_file))


@mcp.tool()
async def merge_audio_video(video_file: str, audio_file: str, ctx: Context) -> str:
    """Replaces a video's sound with an audio file (for dubbing). The video keeps its length: silence is added
    if the audio is shorter, the audio is cut if longer. "Lesson (Hindi).mp3" under "Lesson.mp4" is saved as
    "Lesson (Hindi).mp4". Returns {output_file}."""
    return json.dumps(await progress.run(ctx, clips.merge_audio_video, video_file, audio_file))


Language = Literal["English", "Kannada", "Hindi", "French", "Spanish", "Tamil"]
Speed = Literal["little_slower", "slower", "as_made"]


@mcp.tool()
def list_voices() -> str:
    """The saved voices (names to pass as `voice`) and the folder they are in. Returns {voices, folder}."""
    try:
        return json.dumps(voices.list_voices())
    except Exception as e:
        raise progress.plain_error(e) from e


@mcp.tool()
async def save_voice(source_file: str, name: str, consent: bool, ctx: Context) -> str:
    """Saves a voice from an audio or video file of one person speaking: the clearest 30 seconds, without the
    silence around it, as Documents/VideoAudioAgents/voices/<name>.wav. Needs at least 10 seconds of speech.
    consent must be true: only after the person confirmed it is their own voice or they have the speaker's
    permission. Never replaces a saved voice ("name (2)"). Returns {voice, sample_file, seconds}."""
    return json.dumps(await progress.run(ctx, voices.save_voice, source_file, name, consent))


@mcp.tool()
async def record_voice(name: str, consent: bool, ctx: Context, seconds: int = 20) -> str:
    """Records the computer's microphone and saves it as a voice, like save_voice. It waits up to a minute for the
    person to start speaking, then records `seconds` (10 to 30). consent must be true, as for save_voice.
    Returns {voice, sample_file, seconds}."""
    return json.dumps(await progress.run(ctx, voices.record_voice, name, seconds, consent))


@mcp.tool()
async def speak(voice: str, language: Language, ctx: Context, text: str | None = None,
                transcript_file: str | None = None, speed: Speed = "little_slower",
                output_name: str | None = None) -> str:
    """Reads text aloud in a saved voice, as an .mp3. Give `text`, or `transcript_file` (a transcript or any text
    file; "[12.5s]" times are not read). Saved as "<name> (<voice> voice).mp3" next to the file, or in
    Documents/VideoAudioAgents/Speech/ for text. English, Hindi, French and Spanish are spoken directly in the voice;
    Kannada and Tamil are read by an online reader voice and then changed into it (a weaker match).
    speed: little_slower (default, sounds most natural), slower, as_made. Slow: about 5 to 8 seconds of work per
    second of speech. Returns {output_file, seconds}."""
    return json.dumps(await progress.run(ctx, speech.speak, voice, language, speed, text, transcript_file,
                                         output_name))


@mcp.tool()
async def speak_timed(segments_file: str, voice: str, language: Language, ctx: Context,
                      speed: Speed = "little_slower") -> str:
    """Dubbing: speaks every line of a translated .segments.json (from translated_segments) in a saved voice and
    puts each at its line's start time, so it follows the original video. A line too long for its time is sped up
    a little (at most 1.15 times); lines that still run over are listed in `overruns`. language is the language
    of the lines. Saved as "<segments name> (<voice> voice).mp3"; then merge_audio_video puts it under the video.
    Returns {output_file, seconds, lines, overruns, overrun_count}."""
    return json.dumps(await progress.run(ctx, speech.speak_timed, segments_file, voice, language, speed))


@mcp.tool()
async def change_voice(file: str, voice: str, ctx: Context, speed: Speed = "as_made") -> str:
    """Changes the voice in an audio or video file into a saved voice: the same words and timing, silence stays
    silence. Saved as "<name> (<voice> voice).mp3" next to the file. Returns {output_file, seconds}."""
    return json.dumps(await progress.run(ctx, speech.change_voice, file, voice, speed))


def setup_logging() -> None:
    """Details and tracebacks go to <data>/engine.log, never to the screen (stdout carries the MCP messages)."""
    handler = logging.handlers.RotatingFileHandler(data_dir() / "engine.log", maxBytes=2_000_000, backupCount=1,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])


def printer(prefix: str):
    """A progress reporter for the setup command: prints a line at every 10%."""
    shown = [-1]

    def report(percent, message):
        step = int(percent) // 10 * 10
        if step != shown[0]:
            shown[0] = step
            print(f"  {prefix}: {step}%", flush=True)
    return report


def warm(mode: str) -> None:
    """Downloads ffmpeg and the models for the setup mode. Skips whatever is already there, so it is safe to re-run."""
    print("ffmpeg (the video tool): " + ("already here" if models.ffmpeg_present() else "downloading"), flush=True)
    models.ensure_ffmpeg(printer("ffmpeg"))
    names = models.STANDARD if mode == "standard" else models.FULL
    for name in names:
        label = models.MODELS[name]["label"]
        if models.is_present(name):
            print(f"{label}: already here", flush=True)
            continue
        print(f"{label}: downloading {models.missing_gb([name])} GB", flush=True)
        models.ensure([name], printer(label))
    print(f"Done. Models are in {models.models_dir()}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="video-audio-engine", description="The Video Audio Agents engine.")
    parser.add_argument("--warm", choices=["standard", "full"],
                        help="download ffmpeg and the models for this setup mode, then exit")
    parser.add_argument("--check", action="store_true", help="print what is installed and missing, then exit")
    parser.add_argument("--data", help="the plugin's private data folder (the setup skill passes it)")
    args = parser.parse_args()
    if args.data:
        os.environ["VAA_DATA"] = args.data
    setup_logging()
    if not (args.warm or args.check):
        mcp.run()  # talks to Claude over stdin/stdout
        return
    try:
        if args.warm:
            warm(args.warm)
        print(json.dumps(setup_check.check_setup(), indent=2))
    except Exception as e:
        logging.getLogger("engine").exception("Setup failed")
        print(f"Setup stopped: {e}\nThe details are in {data_dir() / 'engine.log'}. Running it again is safe.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
