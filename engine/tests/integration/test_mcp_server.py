"""Starts the engine exactly as Claude Code does (over stdin/stdout) and talks to it with the MCP client."""
import json
import os
import sys

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def talk_to_engine(data_dir):
    params = StdioServerParameters(command=sys.executable, args=["-m", "video_audio_engine.server"],
                                   env={"VAA_DATA": str(data_dir), "PATH": os.environ.get("PATH", "")})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [tool.name for tool in (await session.list_tools()).tools]
            result = await session.call_tool("check_setup", {})
            return tools, result


def test_engine_starts_lists_its_tools_and_answers_check_setup(private_data):
    tools, result = anyio.run(talk_to_engine, private_data)
    assert "check_setup" in tools
    assert not result.is_error
    check = json.loads(result.content[0].text)
    expected = {"ok", "python", "ffmpeg", "deno", "browser", "models_present", "models_missing_gb",
                "free_ram_gb", "free_disk_gb", "gpu", "notes"}
    assert expected <= set(check)
    assert check["python"].startswith("3.11")
    assert check["models_present"] == []  # a fresh data folder has no models
    assert check["models_missing_gb"]["small"] == 0.5
    assert (private_data / "engine.log").exists()
