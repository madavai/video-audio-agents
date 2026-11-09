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

Three options are installed only on request: `gpu` (transcripts on an NVIDIA graphics card), `speakers` (who said
what) and `indic` (Kannada spoken directly in a saved voice). The data folder remembers them, so a later setup (after
an update) keeps them instead of removing them. `speakers` and `indic` need the person's Hugging Face key: a small
window asks for it, so it never passes through the chat.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine"
OPTIONS = ("gpu", "speakers", "indic")
KEY_FILE = "hugging-face-key.txt"  # the engine's models.py reads the same file


def options(data, add=None):
    """The setup options chosen so far, kept in <data>/setup-options.json. `add` records one more."""
    file = data / "setup-options.json"
    chosen = json.loads(file.read_text(encoding="utf-8")) if file.exists() else []
    if add and add not in chosen:
        chosen.append(add)
        data.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(chosen), encoding="utf-8")
    return [option for option in OPTIONS if option in chosen]


def uv_steps(step, data):
    """The uv commands a step runs, in order."""
    project = ["--frozen", "--no-active", "--project", str(ENGINE)]  # --no-active: ignore another tool's VIRTUAL_ENV
    engine = ["run", *project, "video-audio-engine"]
    packages = ["sync", *project, *[arg for option in options(data) for arg in ("--extra", option)]]
    if step == "packages":
        return [packages]
    if step in ("standard", "full", "speakers", "indic"):  # an option: its packages first, then its models (key)
        warm = [*engine, "--warm", step, "--data", str(data)]
        return [packages, warm] if step in OPTIONS else [warm]
    if step == "gpu":
        return [packages, [*engine, "--check", "--data", str(data)]]
    if step == "browser":
        return [["run", *project, "playwright", "install", "chromium"]]
    if step == "serve":
        return [["run", *project, "--quiet", "video-audio-engine"]]
    sys.exit(f"Unknown step {step!r}: use packages, standard, full, gpu, speakers, indic, browser or serve.")


def ask_key(data):
    """A small window where the person pastes their Hugging Face key, kept only in the data folder. A window, not
    the chat: what is typed in the chat is kept in the conversation. False if they closed it without a key."""
    import tkinter as tk
    root, got = tk.Tk(), {}
    root.title("Video Audio Agents: Hugging Face key")
    root.attributes("-topmost", True)
    tk.Label(root, justify="left", padx=16, pady=12,
             text="Paste your Hugging Face read key (it starts with hf_), then click Save.\n"
                  "It is kept only on this computer, in Video Audio Agents' private folder.").pack()
    entry = tk.Entry(root, show="*", width=50)
    entry.pack(padx=16)
    message = tk.Label(root, fg="#b00020")
    message.pack()

    def save(_=None):
        key = entry.get().strip()
        if key.startswith("hf_") and len(key) > 10 and not any(c.isspace() for c in key):
            got["key"] = key
            root.destroy()
        else:
            message.config(text="That isn't a Hugging Face key: copy the one that starts with hf_.")

    tk.Button(root, text="Save", width=12, command=save).pack(pady=12)
    root.bind("<Return>", save)
    # Once the window is shown: a Mac only gives the keyboard to a window started from a command when asked to.
    root.after(300, lambda: (root.lift(), entry.focus_force()))
    root.mainloop()
    if "key" not in got:
        return False
    data.mkdir(parents=True, exist_ok=True)
    (data / KEY_FILE).write_text(got["key"], encoding="utf-8")
    if os.name != "nt":
        (data / KEY_FILE).chmod(0o600)
    return True


def prepare(step, data):
    """What a step needs before its uv commands: the graphics card is there, the key is saved, the option noted."""
    if step == "gpu" and not shutil.which("nvidia-smi"):
        sys.exit("No NVIDIA graphics card was found on this computer, so there is nothing to install.")
    if step in ("speakers", "indic") and not (data / KEY_FILE).exists():
        print("A small window has opened: paste the Hugging Face key there and click Save.", flush=True)
        if not ask_key(data):
            sys.exit("The window was closed without a key, so nothing was set up. Run this step again.")
    if step in OPTIONS:
        options(data, add=step)


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
    prepare(step, data)  # before the commands, so a newly chosen option is installed with the packages
    commands = uv_steps(step, data)
    os.environ["UV_PROJECT_ENVIRONMENT"] = str(data / "venv")
    uv = os.environ.get("UV", "uv")  # uv run puts its own path here, so a uv installed a minute ago works too
    for args in commands:
        if code := subprocess.run([uv, *args]).returncode:
            sys.exit(code)
    sys.exit(0)


if __name__ == "__main__":
    main()
