"""The setup skill's install steps, run as `uv run --no-project --python 3.11 install.py <step> <data folder>`, and
the engine's start command (`serve`, which plugin.json gives Claude Code).

The engine's environment goes in <data>/venv, the same place plugin.json gives the server: the plugin folder is
replaced on every update, the data folder is kept. uv takes that place only from UV_PROJECT_ENVIRONMENT, and setting a
variable in PowerShell always asks the person first, so this script sets it and the skill's commands stay plain `uv`
commands in both shells. Standard library only: it runs before the engine's packages exist.

Until the setup has installed the engine's packages, `serve` answers as a small stand-in whose one tool, check_setup,
says what to do. Building the packages takes minutes, longer than Claude Code waits for a server to start, and Claude
Code skips a plugin's server that failed for the next 15 minutes, so a failed start before the setup would leave the
engine off after the restart the setup asks for.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine"


def uv_args(step, data):
    project = ["--frozen", "--no-active", "--project", str(ENGINE)]  # --no-active: ignore another tool's VIRTUAL_ENV
    if step == "packages":
        return ["sync", *project]
    if step in ("standard", "full"):
        return ["run", *project, "video-audio-engine", "--warm", step, "--data", str(data)]
    if step == "browser":
        return ["run", *project, "playwright", "install", "chromium"]
    if step == "serve":
        return ["run", *project, "--quiet", "video-audio-engine"]
    sys.exit(f"Unknown step {step!r}: use packages, standard, full, browser or serve.")


def installed(data):
    """Whether the setup has installed the engine's packages (the engine's own command is there)."""
    venv = data / "venv"
    return (venv / "Scripts" / "video-audio-engine.exe").exists() or (venv / "bin" / "video-audio-engine").exists()


def stand_in(data):
    """A minimal MCP server over stdin/stdout (one JSON message per line) until the setup has run."""
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    tool = {"name": "check_setup", "description": "Says what is needed before Video Audio Agents can work.",
            "inputSchema": {"type": "object", "properties": {}}}
    for line in sys.stdin:
        message = json.loads(line) if line.strip() else {}
        if "id" not in message:
            continue  # notifications need no answer
        method, reply = message.get("method"), {"jsonrpc": "2.0", "id": message["id"]}
        if method == "initialize":
            reply["result"] = {"protocolVersion": message["params"]["protocolVersion"],
                               "capabilities": {"tools": {}}, "serverInfo": {"name": "engine", "version": "setup"},
                               "instructions": "Video Audio Agents isn't set up yet: call check_setup."}
        elif method == "tools/list":
            reply["result"] = {"tools": [tool]}
        elif method == "tools/call":
            note = ("The setup has finished: restart Claude Code (close it and open it again) so the engine starts."
                    if installed(data) else
                    'The engine isn\'t installed yet: say "set up video audio agents", then restart Claude Code.')
            check = {"ok": False, "notes": [note]}
            reply["result"] = {"content": [{"type": "text", "text": json.dumps(check)}]}
        elif method == "ping":
            reply["result"] = {}
        else:
            reply["error"] = {"code": -32601, "message": "The engine isn't set up yet."}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


def main():
    step, data = sys.argv[1], Path(sys.argv[2])
    if step == "serve" and not installed(data):
        return stand_in(data)
    os.environ["UV_PROJECT_ENVIRONMENT"] = str(data / "venv")
    uv = os.environ.get("UV", "uv")  # uv run puts its own path here, so a uv installed a minute ago works too
    sys.exit(subprocess.run([uv, *uv_args(step, data)]).returncode)


if __name__ == "__main__":
    main()
