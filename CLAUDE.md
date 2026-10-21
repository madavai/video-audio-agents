# video-audio-agents

Four Claude Code agents (transcriber, translator, voice, publisher), one setup skill and one Python MCP engine. Users are non-developers.

## Rules
- Simple code. No abstractions for single use. No frameworks beyond the MCP SDK. If a change could be 50 lines, it is not 200.
- Every tool returns small JSON; every long step reports progress; every job can be stopped (Esc) and leaves no partial files.
- Never overwrite a user's file: use paths.free_path(). One folder per link.
- Models and binaries are never committed; every download goes through models.py with progress and resume.
- Never print or log secrets, cookies or the browser profile. Never commit .venv, outputs, profiles.
- Plain-English errors for users; tracebacks go to the log file only.
- The agents never post to any platform and never fetch music or images from the internet.
- Any change to a feature updates the agent file that uses it, the USER-GUIDE and the CHANGELOG in the same PR.
- Tests: `uv run pytest` before every PR; `-m slow` for voice tests when models are present.
- Versions are pinned (uv.lock). Bump `version` in plugin.json for every release, or users never receive the update.
- Windows first; keep paths and subprocess calls cross-platform (pathlib, no shell=True).
- Build in the order of docs/BUILD-PLAN.md; do not start a Wave 2 item during Wave 1.

## How the engine is put together
- `engine/src/video_audio_engine/server.py` holds the tool definitions only; each calls a module.
- Slow tools run their work through `progress.run(ctx, work)`: it runs `work(job)` in a thread, sends progress at every 1%, and on Esc makes `job.report()` raise `Stopped` so the work can remove partial files.
- Raise `ToolError("one plain sentence")` for failures the person should read; anything else is logged to `<data>/engine.log` and reported as "Something went wrong".
- stdout carries the MCP messages: never `print` from code the server runs.
- The private data folder is `VAA_DATA` (Claude Code passes `${CLAUDE_PLUGIN_DATA}`); `paths.data_dir()` reads it.
- Models live in `<data>/models/<repo name>/`, pinned to an exact revision with exact file sizes in `models.MODELS`. ffmpeg lives in `<data>/bin/`.
