---
name: setup
description: Sets up Video Audio Agents on this computer (installs the engine and downloads its models). Use right after the plugin is installed or updated, or when the person says "set up video audio agents" (standard) or "set up video audio agents with voice" (full). Also use when check_setup reports something missing, and for the three options installed only on request - "set up the graphics card" (faster transcripts on an NVIDIA card), "set up speaker labels" (who said what, with a free Hugging Face key) and "set up the Kannada voice" (Kannada spoken directly in a saved voice, with a free Hugging Face key).
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
   - next: "Restart Claude Code (close it and open it again) so the engine starts. Then type /mcp: `engine` should show as connected." (Until this restart, the engine is a stand-in that only says to run the setup.) If uv was newly installed in step 1, also say: "If `engine` shows as failed, choose it in /mcp and pick Reconnect." (The engine couldn't start before uv was there, and Claude Code waits up to 15 minutes before trying a failed server again.) On a Mac, when uv was newly installed, also say to close the Terminal window Claude Code runs in (or quit the Claude app with Cmd+Q) and open a new one, because a window opened before uv was installed can't find it.
   - something to try: "Paste a YouTube link and ask for the video and a transcript."

## Login browser (only on request)

Pages behind a login open in Edge or Chrome. If check_setup reports `"browser": null` and the person wants to download from such pages, or they ask to "set up the login browser", install Playwright's own Chromium (about 150 MB):
`uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" browser "${CLAUDE_PLUGIN_DATA}"`

## Graphics card (only on request)

"Set up the graphics card", or yes to check_setup's note that an NVIDIA graphics card was found. It downloads NVIDIA's
maths library (about 0.6 GB; 0.9 GB on disk), so transcripts run on the card: on a recent card about 10 to 20 times
faster. Voice work and speaker labels stay on the processor. Run the standard setup first. Then:
`uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" gpu "${CLAUDE_PLUGIN_DATA}"`

It ends with the JSON check: `gpu_usable` true means it worked. Say so, and that the engine starts using the card
after a restart of Claude Code. If it says no NVIDIA card was found, there is nothing to install: say so in one line.

## Speaker labels (only on request)

"Set up speaker labels", "who said what", or check_setup's `speaker_labels` is false when they want it. It installs
the speaker model's packages (about 1 GB) and downloads its models (33 MB). The models are free but gated on Hugging
Face: the person needs their own account, must accept two models' terms, and makes a key. You can't do these for
them. Run the standard setup first.

1. Tell them, as numbered steps, and wait until they say they're done:
   1. Make a free account at https://huggingface.co/join (skip if they have one).
   2. Logged in, open https://huggingface.co/pyannote/segmentation-3.0 and accept its terms (approval is instant).
   3. The same on https://huggingface.co/pyannote/speaker-diarization-3.1.
   4. At https://huggingface.co/settings/tokens choose Create new token, type "Read", any name, Create, and copy it.
   Say: "Don't paste the key here in the chat: a small window will open for it."
2. Run:
   `uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" speakers "${CLAUDE_PLUGIN_DATA}"`
   Say a small window has opened (on a Mac, click into it first): paste the key there and click Save. The key is kept only in the plugin's private
   folder on this computer and is sent only to Hugging Face, only to download these two models. Then the packages
   install (several minutes) and the models download.
3. If it stops because Hugging Face refused, say what its message says to do (accept the terms on the pages it
   names, or a new key), then run step 2 again: it asks for the key again only when the old one was refused.

If the person pastes the key in the chat anyway: don't repeat it or use it. Tell them it is now in this conversation,
and suggest they delete that key on https://huggingface.co/settings/tokens and make a new one for the window.

Finish as in step 4 above: `speaker_labels` true in the JSON check, and a restart of Claude Code so the engine has it.

## Kannada voice (only on request)

"Set up the Kannada voice", "Kannada in my own voice", or check_setup's `kannada_voice` is false when they want it.
Without it, Kannada is read by an online reader voice and then changed into the saved voice (a weaker match). With
it, IndicF5, a speech model made by AI4Bharat at IIT Madras, speaks Kannada directly in the saved voice. It installs
about 0.3 GB of packages and downloads the model (1.4 GB), and the accurate speech-to-text model (1.6 GB, which checks
each Kannada reading) if the full setup hasn't already. Tamil isn't part of it: Tamil keeps the reader voice. Run
the standard setup first.

1. Before anything, tell them plainly, and ask "Go ahead?":
   - IndicF5's makers publish it as free to use (the MIT licence), but they built it from another model, F5-TTS,
     whose makers allow only non-commercial use. So it may be fine only for personal, non-commercial use: for videos
     they earn money from, they should check the licence first (or ask a lawyer).
   - Like all voice work here, it only copies a voice with the person's permission.
2. The model is free but gated on Hugging Face: they need their own account, accept its terms, and need a key. One
   key serves both this and speaker labels: if they saved one for speaker labels, they only accept the terms
   (step 2 below), and no window opens. Tell them, as numbered steps, and wait until they say they're done:
   1. Make a free account at https://huggingface.co/join (skip if they have one).
   2. Logged in, open https://huggingface.co/ai4bharat/IndicF5 and accept its terms (it shares their name and email
      with AI4Bharat; approval is instant).
   3. Unless they saved a key for speaker labels: at https://huggingface.co/settings/tokens choose Create new token,
      type "Read", any name, Create, and copy it. Say: "Don't paste the key here in the chat: a small window will
      open for it."
3. Run:
   `uv run --no-project --python 3.11 "${CLAUDE_PLUGIN_ROOT}/skills/setup/install.py" indic "${CLAUDE_PLUGIN_DATA}"`
   If no key was saved before, say a small window has opened (on a Mac, click into it first): paste the key there and
   click Save. Then the packages install (a few minutes) and the model downloads.
4. If it stops because Hugging Face refused, or the key is pasted in the chat, do as for speaker labels above.

Finish as in step 4 above: `kannada_voice` true in the JSON check, and a restart of Claude Code. Then say: each saved
voice needs one reading of a short Kannada sentence, once; the voice helper shows the sentence and records it
("record the Kannada sentence for my voice"). Until a voice has it, its Kannada is still made with the reader voice.

## If something fails

Say which step failed and why, in one sentence (for example "the internet connection dropped during the download"). Then: "Running the setup again continues where it stopped." The details are in `${CLAUDE_PLUGIN_DATA}/engine.log`. Do not try other install methods or edit any files.

## Updates

"Update video audio agents": run `claude plugin marketplace update madavai`, then `claude plugin update video-audio-agents@madavai`, then this setup again (it only installs what changed, and keeps the graphics-card, speaker-label and Kannada voice options if they were set up), then ask the person to restart Claude Code.
