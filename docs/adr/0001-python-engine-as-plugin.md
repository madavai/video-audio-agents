# ADR 0001: A Python engine inside a Claude Code plugin

- **Status:** accepted, and in use since release 1.0.0
- **Date:** 2026-10-22 (planned 2026-10-21 in `docs/BUILD-PLAN.md`, revised during the Wave 1 build)

## Context

Video Audio Agents turns links and recordings into video and audio files, transcripts, subtitles, clips,
translations, dubbed versions and social posts. The people using it are not developers: they ask in plain words
in Claude Code, the Claude desktop app or Madav, and expect it to work without installing anything by hand.

Two kinds of work are involved:

- **Thinking work**: translating, summarising, finding chapters, writing posts. The AI model in the person's own
  Claude subscription does this well, in any language, at no extra cost.
- **Heavy media work**: downloading (yt-dlp), speech to text (faster-whisper), voice cloning and speech
  (Chatterbox), cutting and merging (ffmpeg). All of it is native Python or driven from Python, and none of it can
  run inside the AI model.

The product also has to install with one sentence, keep its multi-gigabyte models off GitHub, survive updates
without downloading everything again, and stop cleanly when the person presses Esc.

## Decision

1. **One Claude Code plugin**, installed from this GitHub repository, which is also its own marketplace
   (`madavai`). The plugin holds four agents (transcriber, translator, voice, publisher) and one setup skill, all
   Markdown, plus one MCP server called `engine`.
2. **The engine is Python 3.11**, an MCP server built on the official MCP SDK (2.x, `MCPServer`) and no other
   framework. It does only the heavy media work. Every tool returns a small JSON object, reports progress, stops
   on Esc without leaving half-made files, and never overwrites a file.
3. **The AI model does the thinking work** and hands its text to the engine (`save_text`,
   `translated_segments`), which saves and checks it.
4. **uv runs the engine.** uv installs a private Python and the exact versions in `uv.lock`, the same on every
   computer, so nobody installs Python. The setup skill installs uv itself if it is missing.
5. **Nothing big is in the repository.** Models and ffmpeg are downloaded on the person's computer into the
   plugin's data folder (`${CLAUDE_PLUGIN_DATA}`), which Claude Code keeps across updates.
6. **CPU only, one big model in memory at a time, Windows first.** GPU, Mac and the Wave 2 helpers come in 1.1.

### Alternatives considered

- **A TypeScript or Node engine.** Claude Code plugins are often written that way, but every heavy library here
  is Python. A Node engine would still have to start Python for each job, so it would add a second language and a
  second install without removing the first.
- **A separate desktop app.** More to build and maintain, and it would duplicate what Claude Code and Madav's
  Agent Studio already offer as the surface.
- **Paid cloud services** for speech to text, voices or translation. They need keys and cost money per minute;
  the goal is "free beyond your Claude or Madav subscription".
- **whisper.cpp** for speech to text. faster-whisper measured 2.5 times faster on the same computer, with fewer
  word errors at the accurate setting (5.1% against 6.7%).

## Consequences

- One language for all engine code and its tests (`tests/` at the repository root, run with pytest on Windows and
  Ubuntu in CI).
- The first setup downloads about 3 GB (about 10 GB with voice). Setup names the sizes before it starts, shows
  progress and continues a broken download.
- The engine must start within Claude Code's MCP start limit, so setup builds its environment before the first
  start; the engine never builds it on demand.
- Libraries that like to download their own files have to be stopped from doing so, or the person would wait
  without progress and the engine could break offline (see below).
- The plugin works wherever Claude Code plugins load: Claude Code, the Claude desktop app, and Madav once its chat
  loads the person's plugins (checked separately, outside this repository).

## What changed during the build

The plan was right about the shape. These five choices were changed when the build ran into real files and real
computers. `docs/BUILD-PLAN.md` has been updated to match.

### 1. Models are downloaded directly, pinned to an exact version and exact sizes

- **Planned:** let the libraries download their models through `huggingface-hub`, with `HF_HOME` pointed at the
  data folder.
- **Built:** `models.py` lists every model's Hugging Face repository at a fixed revision and every file with its
  exact size in bytes. It downloads each file from that revision's address with plain `urllib`, into
  `<data>/models/<repository name>/`, resuming a `.part` file and renaming it only when complete. The libraries
  then load from that folder (`WhisperModel(<folder>)`, Chatterbox's `from_local(<folder>, "cpu")`, never
  `from_pretrained`).
- **Why:** a library's own download shows the person no progress, can't be stopped cleanly, fetches whatever is
  newest, and tells us nothing about how much is still missing. With exact sizes, `check_setup` can say exactly
  how many GB a job will download, a half-finished file is never mistaken for a whole one, and the tests serve the
  same files from a local server (`VAA_MODELS_URL`). For the same reason the multilingual voice model's Chinese
  converter is switched off: it fetched a word list from the internet on every first load, for a language the
  plugin doesn't offer.

### 2. Transcript lines are built from word timings

- **Planned:** one transcript line per faster-whisper segment, with the segment's start time.
- **Built:** `transcribe` asks for word timings and builds its own sentence-sized lines: a new line after a
  sentence ends (once it has lasted a second), at a pause of over a second, or before a line would run past 12
  seconds.
- **Why:** with the batched pipeline (needed for speed), segment timings dropped words at the edges of each
  chunk. Word timings keep every word, and sentence lines are what subtitles, translation and dubbing work best
  with.

### 3. Transcription uses 4 threads

- **Planned:** `cpu_threads = max(4, cores // 2)`.
- **Built:** always 4 threads.
- **Why:** on a 24-core PC (12 threads) a 40-minute lesson crashed the whole engine (a stack overflow on Windows,
  with full batches of 8). 4 threads were as fast in measurements and never crashed.

### 4. Translations are checked with `translated_segments`, not written as JSON by the AI

- **Planned:** for translated subtitles and dubbing, the translator agent translates the `.segments.json` file
  itself and saves the result as JSON.
- **Built:** the translator writes the translation the same way as the transcript, one `[12.5s] text` line per
  original line, saved in parts. The `translated_segments` tool then pairs each line with the original segment
  by its time, writes `<name> (<language>).segments.json` with the original timings, and refuses an incomplete
  translation, naming the missing lines, so the agent adds just those and tries again.
- **Why:** an hour-long transcript is thousands of JSON objects. Having the AI write them is slow, breaks on
  quotation marks and escaping, and a merged or skipped line goes unnoticed. Timestamped lines are what the AI
  translates anyway, and matching by time makes "nothing lost" something the engine checks rather than hopes.

### 5. The plugin has its own folder, and its Python lives in the data folder

- **Planned:** the repository root is the plugin, with the engine's environment in `engine/.venv`, and the engine
  declared in a root `.mcp.json`.
- **Built:** the plugin is `plugins/video-audio-agents/` (manifest, agents, setup skill, engine), and the
  marketplace at the root points there. The engine is declared under `mcpServers` in the plugin's `plugin.json`,
  with `UV_PROJECT_ENVIRONMENT=${CLAUDE_PLUGIN_DATA}/venv`. The setup skill's install steps run through
  `skills/setup/install.py`, which sets the same variable.
- **Why:**
  - Claude Code copies the plugin's whole folder to each computer, so with the root as the plugin everyone also
    received the build plan, the reference apps, the tests and the CI files.
  - The installed plugin folder (`${CLAUDE_PLUGIN_ROOT}`) is replaced on every update, so a 3 GB environment
    inside it would have been rebuilt after every update. The data folder is kept.
  - A root `.mcp.json` was also read as the project's own MCP config whenever Claude Code was opened in the
    repository, where the plugin variables are not filled in, so `engine` showed as failed.
  - PowerShell asks the person before any `$env:` assignment, whatever the skill pre-approves, so the variable
    is set inside `install.py` and the skill's commands stay plain `uv` commands.

### Smaller changes that follow from these

- **The version follows the build.** Claude Code offers an update only when `plugin.json`'s version changes, so
  each phase raised the middle number (0.5.0, 0.6.0) and the release is 1.0.0. The version lives only in
  `plugin.json`.
- **One big-model job at a time.** Speech to text and the three voice models share one slot in memory, and a
  second voice or transcript job waits for the first, so a normal computer never holds two multi-gigabyte models.
- **Agents are handed the work.** Agent descriptions say "Use proactively", or the main chat called the engine
  itself. A subagent never hears the person directly, so the voice agent accepts the permission to save a voice
  when the main chat passes on the person's own words.
