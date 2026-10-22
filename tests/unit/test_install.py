"""The setup skill's install.py: every step runs uv with the engine's environment in the data folder."""
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "plugins" / "video-audio-agents" / "skills" / "setup" / "install.py"
spec = importlib.util.spec_from_file_location("install", SCRIPT)
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)


def test_the_engine_is_found_from_the_script():
    assert (install.ENGINE / "pyproject.toml").is_file()


@pytest.mark.parametrize("step", ["packages", "standard", "full", "browser"])
def test_each_step_uses_the_environment_in_the_data_folder(step, tmp_path, monkeypatch):
    seen = {}

    def run(args):
        seen["args"], seen["venv"] = args, os.environ["UV_PROJECT_ENVIRONMENT"]
        return subprocess.CompletedProcess(args, 0)

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


def test_an_unknown_step_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="Unknown step"):
        install.uv_args("everything", tmp_path)
