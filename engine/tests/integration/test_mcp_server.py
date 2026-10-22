"""Starts the engine exactly as Claude Code does (over stdin/stdout) and talks to it with the MCP client."""
import json
import os
import sys

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

TOOLS = {"check_setup", "fetch_media", "transcribe", "save_text", "make_subtitles", "cut_clip", "merge_audio_video",
         "translated_segments"}


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
                "free_ram_gb", "free_disk_gb", "gpu", "notes"}
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
