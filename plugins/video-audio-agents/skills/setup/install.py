"""The setup skill's install steps, run as `uv run --no-project --python 3.11 install.py <step> <data folder>`.

The engine's environment goes in <data>/venv, the same place plugin.json gives the server: the plugin folder is
replaced on every update, the data folder is kept. uv takes that place only from UV_PROJECT_ENVIRONMENT, and setting a
variable in PowerShell always asks the person first, so this script sets it and the skill's commands stay plain `uv`
commands in both shells. Standard library only: it runs before the engine's packages exist.
"""
import os
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine"


def uv_args(step, data):
    project = ["--frozen", "--project", str(ENGINE)]
    if step == "packages":
        return ["sync", *project]
    if step in ("standard", "full"):
        return ["run", *project, "video-audio-engine", "--warm", step, "--data", str(data)]
    if step == "browser":
        return ["run", *project, "playwright", "install", "chromium"]
    sys.exit(f"Unknown step {step!r}: use packages, standard, full or browser.")


def main():
    step, data = sys.argv[1], Path(sys.argv[2])
    os.environ["UV_PROJECT_ENVIRONMENT"] = str(data / "venv")
    uv = os.environ.get("UV", "uv")  # uv run puts its own path here, so a uv installed a minute ago works too
    sys.exit(subprocess.run([uv, *uv_args(step, data)]).returncode)


if __name__ == "__main__":
    main()
