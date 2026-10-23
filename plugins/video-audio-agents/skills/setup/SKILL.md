---
name: setup
description: Sets up Video Audio Agents on this computer (installs the engine and downloads its models). Use right after the plugin is installed or updated, or when the person says "set up video audio agents" (standard) or "set up video audio agents with voice" (full). Also use when check_setup reports something missing.
allowed-tools:
  - Bash(uv *)
  - Bash(~/.local/bin/uv *)
  - Bash(powershell *)
  - Bash(curl *)
  - PowerShell(uv *)
  - PowerShell(~/.local/bin/uv *)
  - mcp__plugin_video-audio-agents_engine__check_setup
---

# Set up Video Audio Agents

The person may not be technical. Keep every message short and plain. Never show raw errors: say what failed in one sentence and give the log path.

The plugin lives at `${CLAUDE_PLUGIN_ROOT}`; its private data folder is `${CLAUDE_PLUGIN_DATA}`. Run each command below exactly as written, one per call, with nothing added (these exact commands are pre-approved). Use the Bash tool if you have it, otherwise PowerShell.

The install steps run through `install.py` beside this file: it puts the engine's private Python in the data folder (`venv`), where plugin updates don't remove it. Never run `uv sync` or `uv run` on the engine directly: that would build a second 3 GB copy inside the plugin.

## Choose the mode

- **Standard** (default, "set up video audio agents"): about 3 GB. Downloading, transcripts, subtitles, translations and posts work straight away. Voice models download on first use.
- **Full** ("... with voice", "full setup"): about 10 GB. Also downloads the accurate transcript model, the three voice models and the music keeper for dubs, so voice work starts without waiting.

Tell the person which mode and its size before starting. Re-running setup is always safe: it skips whatever is already there.

## Steps

1. **uv** (the small program that installs the engine's private Python):
   run `uv --version`. If it is missing:
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - macOS or Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

   Then use `~/.local/bin/uv` in place of `uv` for the rest of this setup, because the current window doesn't know the new program yet. Remember that uv was newly installed (step 4).

2. **Engine packages** (about 2 to 3 GB the first time; takes several minutes):
   `uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" packages "${CLAUDE_PLUGIN_DATA}"`

3. **ffmpeg and models** (prints each item, its size and progress):
   - Standard: `uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" standard "${CLAUDE_PLUGIN_DATA}"`
   - Full: the same with `full` in place of `standard`.

   Steps 2 and 3 can take a long time. Tell the person what is downloading. If you run one in the background, wait for it to finish before the next step, and never end your turn while one is still running: setup is only done when step 3 has printed its JSON check.

4. **Finish.** The last thing step 3 prints is a JSON check. Tell the person, in plain words:
   - "Setup complete", the mode, and roughly how much was downloaded;
   - where their files will be saved (`output_folder` from the check);
   - anything in `notes` (for example, no Edge or Chrome found);
   - next: "Restart Claude Code (close it and open it again) so the engine starts. Then type /mcp: `engine` should show as connected." (Until this restart, the engine is a stand-in that only says to run the setup.) If uv was newly installed in step 1, also say: "If `engine` shows as failed, choose it in /mcp and pick Reconnect." (The engine couldn't start before uv was there, and Claude Code waits up to 15 minutes before trying a failed server again.)
   - something to try: "Paste a YouTube link and ask for the video and a transcript."

## Login browser (only on request)

Pages behind a login open in Edge or Chrome. If check_setup reports `"browser": null` and the person wants to download from such pages, or they ask to "set up the login browser", install Playwright's own Chromium (about 150 MB):
`uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" browser "${CLAUDE_PLUGIN_DATA}"`

## If something fails

Say which step failed and why, in one sentence (for example "the internet connection dropped during the download"). Then: "Running the setup again continues where it stopped." The details are in `${CLAUDE_PLUGIN_DATA}/engine.log`. Do not try other install methods or edit any files.

## Updates

"Update video audio agents": run `claude plugin marketplace update madavai`, then `claude plugin update video-audio-agents@madavai`, then this setup again (it only installs what changed), then ask the person to restart Claude Code.
