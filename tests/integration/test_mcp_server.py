"""Starts the engine exactly as Claude Code does (over stdin/stdout) and talks to it with the MCP client."""
import json
import os
import subprocess
import sys

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

TOOLS = {"check_setup", "fetch_media", "transcribe", "save_text", "make_subtitles", "cut_clip", "merge_audio_video",
         "translated_segments", "list_voices", "save_voice", "record_voice", "speak", "speak_timed", "change_voice",
         "list_links", "search_texts", "clean_audio", "crop_vertical", "mix_music", "export_podcast",
         "set_pronunciations", "label_speakers"}


async def talk_to_engine(data_dir, calls):
    """Runs the tool calls in order; each call's arguments may use the previous result. Returns results and
    the progress messages per call."""
    params = StdioServerParameters(command=sys.executable, args=["-m", "video_audio_engine.server"],
                                   env={"VAA_DATA": str(data_dir), "PATH": os.environ.get("PATH", "")})
    results, progress = [], []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            for name, arguments in calls:
                messages = []

                async def on_progress(value, total, message, messages=messages):
                    messages.append(message)

                previous = json.loads(results[-1].content[0].text) if results else None
                result = await session.call_tool(name, arguments(previous) if callable(arguments) else arguments,
                                                 progress_callback=on_progress)
                results.append(result)
                progress.append(messages)
    return tools, results, progress


def test_engine_starts_lists_its_tools_and_answers_check_setup(private_data):
    tools, results, _ = anyio.run(talk_to_engine, private_data, [("check_setup", {})])
    assert TOOLS <= tools
    assert not results[0].is_error
    check = json.loads(results[0].content[0].text)
    expected = {"ok", "python", "ffmpeg", "deno", "browser", "models_present", "models_missing_gb",
                "free_ram_gb", "free_disk_gb", "gpu", "gpu_usable", "speaker_labels", "notes"}
    assert expected <= set(check)
    assert check["python"].startswith("3.11")
    assert check["models_present"] == []  # a fresh data folder has no models
    assert check["models_missing_gb"]["small"] == 0.5
    assert (private_data / "engine.log").exists()


def test_download_then_transcribe_with_progress(with_models, web, tmp_path):
    calls = [
        ("fetch_media", {"url": f"{web}/talk.mp3", "save": "audio", "folder": str(tmp_path)}),
        ("transcribe", lambda fetched: {"file": fetched["files"][0], "accuracy": "fast"}),
    ]
    _, results, progress = anyio.run(talk_to_engine, with_models, calls)
    assert not results[0].is_error and not results[1].is_error, results
    transcript = json.loads(results[1].content[0].text)
    assert "country" in (tmp_path / "talk" / "talk.txt").read_text(encoding="utf-8")
    assert transcript["language"] == "en"
    assert progress[0] and progress[1][-1] == "Transcript ready"


def test_a_tool_error_reaches_claude_as_one_plain_sentence(private_data, tmp_path):
    calls = [("transcribe", {"file": str(tmp_path / "nothing.mp3")})]
    _, results, _ = anyio.run(talk_to_engine, private_data, calls)
    assert results[0].is_error
    # The MCP SDK puts "Error executing tool transcribe: " in front; no traceback follows.
    assert results[0].content[0].text.endswith(f": There is no file at {tmp_path / 'nothing.mp3'}.")


def test_a_title_over_60_characters_is_refused_naming_it(private_data, tmp_path):
    folder = tmp_path / "Lesson"
    folder.mkdir()
    (folder / "Lesson.txt").write_text("x")
    titles = "A short title\n" + "Long " * 13
    calls = [("save_text", {"next_to": str(folder / "Lesson.txt"), "label": "titles", "text": titles})]
    _, results, _ = anyio.run(talk_to_engine, private_data, calls)
    assert results[0].is_error
    assert results[0].content[0].text.endswith(': Title 2 ("Long Long Long Long Long Long Long Long...") is 64 '
                                               "characters, over the 60 characters YouTube shows in full; "
                                               "shorten it and save again.")
    assert [p.name for p in folder.iterdir()] == ["Lesson.txt"]


def test_speaker_labels_without_the_option_say_how_to_set_it_up(private_data, copy_of):
    audio = copy_of("talk.mp3")
    segments = audio.with_name("talk.segments.json")
    segments.write_text('[{"start": 0.3, "end": 3.0, "text": "And so my fellow Americans,"}]', encoding="utf-8")
    calls = [("label_speakers", {"file": str(audio), "segments_file": str(segments)})]
    _, results, _ = anyio.run(talk_to_engine, private_data, calls)
    assert results[0].is_error and results[0].content[0].text.endswith(
        'say "set up speaker labels" (it needs a free Hugging Face account).')


def test_details_reach_the_log_file(private_data):
    """The MCP SDK gives the root logger a handler of its own when it loads; the engine's log file still gets
    everything (it stayed empty before, while errors told people to look there)."""
    code = ("import logging; from video_audio_engine import server; server.setup_logging(); "
            "logging.getLogger('engine').error('the details')")
    subprocess.run([sys.executable, "-c", code], env={**os.environ, "VAA_DATA": str(private_data)}, check=True,
                   capture_output=True)
    assert "ERROR engine: the details" in (private_data / "engine.log").read_text(encoding="utf-8")


def test_music_and_podcast_tools_over_mcp_with_progress(with_models, copy_of):
    voice, bed = copy_of("bursts.wav"), copy_of("bed.mp3")
    chapters = voice.with_name("bursts (chapters).md")
    chapters.write_text("00:00 Start\n00:07 Middle\n", encoding="utf-8")
    calls = [
        ("mix_music", {"voice_file": str(voice), "music_file": str(bed), "music_volume": 0.3}),
        ("export_podcast", lambda mixed: {"audio_file": mixed["output_file"], "chapters": str(chapters),
                                          "title": "Hello"}),
    ]
    _, results, progress = anyio.run(talk_to_engine, with_models, calls)
    assert not results[0].is_error and not results[1].is_error, results
    mixed, episode = (json.loads(result.content[0].text) for result in results)
    assert mixed == {"output_file": str(voice.with_name("bursts (with music).mp3")), "seconds": 15.0}
    assert episode["output_file"] == str(voice.with_name("bursts (with music) (podcast).mp3")) and episode["chapters"] == 2
    assert progress[0][-1] == "Mixing the music under the voice: done" and progress[1][-1] == "Making the podcast file: done"


def test_the_pronunciation_tool_takes_word_pairs():
    from video_audio_engine import server
    tools = anyio.run(server.mcp.list_tools)
    schema = next(tool for tool in tools if tool.name == "set_pronunciations").input_schema
    assert schema["properties"]["pairs"]["additionalProperties"] == {"type": "string"}
    assert set(schema["required"]) == {"voice", "pairs"}
