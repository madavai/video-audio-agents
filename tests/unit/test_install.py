"""The setup skill's install.py: every step runs uv with the engine's environment in the data folder, and `serve`
starts the engine, or a stand-in that connects at once until the setup has run."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SCRIPT = Path(__file__).parents[2] / "plugins" / "video-audio-agents" / "skills" / "setup" / "install.py"
spec = importlib.util.spec_from_file_location("install", SCRIPT)
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


def fake_setup(data):
    """What the setup leaves behind that serve looks for: the engine's own command in the environment."""
    command = data / "venv" / ("Scripts/video-audio-engine.exe" if os.name == "nt" else "bin/video-audio-engine")
    command.parent.mkdir(parents=True)
    command.touch()


def test_the_engine_is_found_from_the_script():
    assert (install.ENGINE / "pyproject.toml").is_file()


@pytest.mark.parametrize("step", ["packages", "standard", "full", "browser", "serve"])
def test_each_step_uses_the_environment_in_the_data_folder(step, tmp_path, monkeypatch):
    seen = {}

    def run(args):
        seen["args"], seen["venv"] = args, os.environ["UV_PROJECT_ENVIRONMENT"]
        return subprocess.CompletedProcess(args, 0)

    fake_setup(tmp_path)
    monkeypatch.setattr(install.subprocess, "run", run)
    monkeypatch.setenv("UV", "the-uv-that-started-us")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "somewhere else")  # restored after the test
    monkeypatch.setattr(install.sys, "argv", ["install.py", step, str(tmp_path)])
    with pytest.raises(SystemExit) as done:
        install.main()
    assert done.value.code == 0
    assert seen["venv"] == str(tmp_path / "venv")
    assert seen["args"][0] == "the-uv-that-started-us"
    assert seen["args"][2:6] == ["--frozen", "--no-active", "--project", str(install.ENGINE)]


def test_serve_starts_the_engine_once_the_setup_has_run(tmp_path):
    assert install.uv_args("serve", tmp_path)[-2:] == ["--quiet", "video-audio-engine"]


def test_an_unknown_step_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="Unknown step"):
        install.uv_args("everything", tmp_path)


async def check_twice(data):
    """Connects to serve as Claude Code does, calls check_setup, fakes the setup, calls it again."""
    params = StdioServerParameters(command=sys.executable, args=[str(SCRIPT), "serve", str(data)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name for tool in (await session.list_tools()).tools}
            before = await session.call_tool("check_setup", {})
            fake_setup(data)
            after = await session.call_tool("check_setup", {})
    return tools, json.loads(before.content[0].text), json.loads(after.content[0].text)


def test_before_the_setup_a_stand_in_connects_and_says_what_to_do(tmp_path):
    tools, before, after = anyio.run(check_twice, tmp_path)
    assert tools == {"check_setup"}
    assert not before["ok"] and "set up video audio agents" in before["notes"][0]
    assert not after["ok"] and "restart Claude Code" in after["notes"][0]
    assert not (tmp_path / "venv" / "pyvenv.cfg").exists()  # the stand-in installs nothing
