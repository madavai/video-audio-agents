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


@pytest.fixture
def ran(tmp_path, monkeypatch):
    """Runs install.py's main for a step without running uv: returns each command and the environment it got."""
    seen = []

    def run(args):
        seen.append((args, os.environ["UV_PROJECT_ENVIRONMENT"]))
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(install.subprocess, "run", run)
    monkeypatch.setattr(install.shutil, "which", lambda name: "nvidia-smi" if name == "nvidia-smi" else None)
    monkeypatch.setenv("UV", "the-uv-that-started-us")
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", "somewhere else")  # restored after the test

    def main(step):
        monkeypatch.setattr(install.sys, "argv", ["install.py", step, str(tmp_path)])
        with pytest.raises(SystemExit) as done:
            install.main()
        assert done.value.code == 0
        return seen
    return main


@pytest.mark.parametrize("step", ["packages", "standard", "full", "gpu", "speakers", "indic", "browser", "serve"])
def test_each_step_uses_the_environment_in_the_data_folder(step, tmp_path, ran):
    fake_setup(tmp_path)
    (tmp_path / install.KEY_FILE).write_text("hf_saved_before")  # speakers, indic: the key was given earlier
    for args, venv in ran(step):
        assert venv == str(tmp_path / "venv")
        assert args[0] == "the-uv-that-started-us"
        assert args[2:6] == ["--frozen", "--no-active", "--project", str(install.ENGINE)]


def test_serve_starts_the_engine_once_the_setup_has_run(tmp_path):
    assert install.uv_steps("serve", tmp_path) == [["run", "--frozen", "--no-active", "--project", str(install.ENGINE),
                                                     "--quiet", "video-audio-engine"]]


def test_an_unknown_step_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="Unknown step"):
        install.uv_steps("everything", tmp_path)


def test_the_options_chosen_are_kept_by_later_setups(tmp_path, ran):
    """uv sync removes what isn't asked for, so a setup after an update must ask for the options again."""
    assert ran("gpu")[0][0][1:] == ["sync", "--frozen", "--no-active", "--project", str(install.ENGINE),
                                    "--extra", "gpu"]
    assert ran("gpu")[-1][0][-3:] == ["--check", "--data", str(tmp_path)]  # says whether the card can now be used
    assert ran("packages")[-1][0][-2:] == ["--extra", "gpu"]
    assert install.options(tmp_path) == ["gpu"]


def test_without_an_nvidia_card_there_is_nothing_to_install(tmp_path, monkeypatch):
    monkeypatch.setattr(install.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="No NVIDIA graphics card was found"):
        install.prepare("gpu", tmp_path)
    assert install.options(tmp_path) == []


@pytest.mark.parametrize("step", ["speakers", "indic"])
def test_the_gated_options_ask_for_the_key_in_a_window_once(step, tmp_path, ran, monkeypatch):
    asked = []

    def window(data):
        asked.append(data)
        (data / install.KEY_FILE).write_text("hf_typed_in_the_window")
        return True

    monkeypatch.setattr(install, "ask_key", window)
    commands = [args[1:] for args, _ in ran(step)]
    assert asked == [tmp_path]
    assert commands[0][-2:] == ["--extra", step]  # the packages, then the models (which need the key)
    assert commands[1][-4:] == ["--warm", step, "--data", str(tmp_path)]
    ran(step)
    assert asked == [tmp_path]  # the key is kept: not asked again


def test_the_kannada_voice_reuses_the_key_of_speaker_labels(tmp_path, ran, monkeypatch):
    """One Hugging Face key for both: a person who set up speaker labels isn't asked again, and both options stay."""
    monkeypatch.setattr(install, "ask_key", lambda data: (data / install.KEY_FILE).write_text("hf_key") > 0)
    ran("speakers")
    monkeypatch.setattr(install, "ask_key", lambda data: pytest.fail("asked for the key again"))
    assert ran("indic")[-2][0][-4:] == ["--extra", "speakers", "--extra", "indic"]
    assert install.options(tmp_path) == ["speakers", "indic"]


@pytest.mark.parametrize("step", ["speakers", "indic"])
def test_closing_the_key_window_stops_the_setup(step, tmp_path, monkeypatch):
    monkeypatch.setattr(install, "ask_key", lambda data: False)
    with pytest.raises(SystemExit, match="closed without a key"):
        install.prepare(step, tmp_path)
    assert install.options(tmp_path) == []


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
