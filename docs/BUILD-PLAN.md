# Video Audio Agents — Build Plan

**Repo:** https://github.com/madavai/video-audio-agents (public, MIT)
**Status:** proposal for approval, then the handoff file for the Claude Code build session
**Scope:** the complete product, built in **two waves**. Wave 1 ships as release 1.0, Wave 2 as release 1.1.

---

## 0. How to use this document

1. Chaithru approves this plan (or asks for changes).
2. Clone the empty repo on the PC: `git clone https://github.com/madavai/video-audio-agents.git`
3. Put this file at `docs/BUILD-PLAN.md`, and copy the two proven apps into `docs/reference/`:
   `C:\Audio\Transcriber.pyw` and `C:\Audio\Voice Changer.pyw`. They hold the logic to port (download, naming, cutting long audio, voice sample selection, speed control). Delete `docs/reference/` after 1.0 ships.
4. Open Claude Code in the repo and say: **"Build Phase 1 from docs/BUILD-PLAN.md."** Then Phase 2, and so on. Each phase ends with its tests green and a pull request for review.

Rules for the build session are in §14 (proposed `CLAUDE.md`).

---

## 1. Goal

One open-source package that anyone adds to Claude Code, the Claude desktop app or Madav with one sentence, then uses by asking in plain words:

> "Install https://github.com/madavai/video-audio-agents and set it up."
> "Download the video of this lesson."
> "Transcript of these two links, no timestamps, with chapters and a summary."
> "Translate it to Kannada." · "Dub it into Hindi in my voice."
> "Make three Shorts from the best moments, with subtitles."
> "Write the YouTube title, description, a LinkedIn post and an X thread."

Every link can give any mix of **video (.mp4)**, **audio (.mp3)**, **transcript (.txt)**, **subtitles (.srt)**, clips, translations, dubbed versions and social posts, each link in its own folder, nothing ever overwritten. Everything is free beyond the person's Claude or Madav subscription.

### Not in either wave
- A separate desktop app (Madav's Agent Studio is the visual, House-themed surface).
- Paid services (premium voices, AI images/thumbnails).
- claude.ai in a browser or on phones: the engine runs on the person's own computer.
- Automatic posting to social platforms (possible later; needs each platform's account and approval).

---

## 2. Decisions

| Decision | Choice | Why |
|---|---|---|
| Language | **Python** for the engine, Markdown for agents and skills | Every heavy part (yt-dlp, faster-whisper, Chatterbox, ffmpeg) is native Python or driven from it. One language, one setup. Allowed because this is a standalone add-on, not Madav core. |
| Shape | **Claude Code plugin**: 4 agents, 1 skill, 1 MCP server | Installs from the GitHub link; works in Claude Code, the Claude app (Cowork) and Madav (Madav plugins are Claude Code plugins). |
| Agents | `transcriber`, `translator`, `voice`, `publisher` | Four clear jobs. The main chat coordinates; a multi-step request runs them in order. |
| Thinking work | **the AI model does it**: translation, summaries, chapters, best moments, posts | Free, any language, no keys. |
| Speech-to-text | **faster-whisper**, batched, silence skipped; `large-v3-turbo` for Accurate | Measured 2.5× faster than whisper.cpp; 5.1% vs 6.7% word errors for Accurate. |
| Voice | **Chatterbox** on the computer | Proven in the Voice Changer app; free. |
| Cutting, subtitles, merging, loudness, music | **ffmpeg** (bundled via PyPI) | One tool for every media edit, no manual install. |
| Setup | **uv** creates a private Python and installs pinned versions | Nobody installs Python; locked versions behave the same on every PC. |
| Models and binaries | **Never in the repo.** Downloaded by the setup skill or on first use into the plugin's private folder (§8) | GitHub can't hold multi-GB files, and clones must stay small. |
| Where files go | `~/Documents/VideoAudioAgents/<title>/…` (one folder per link); voices in `~/Documents/VideoAudioAgents/voices/` | One place per video for all its outputs; visible; a call can name another folder. |
| Private state | `${CLAUDE_PLUGIN_DATA}` → `~/.claude/plugins/data/video-audio-agents/` | Models, browser login profile, logs. Survives updates; never in the repo. |
| Code style | Simple. No frameworks beyond the MCP SDK. No abstractions for one-time use. | Owner's standing rule. |

---

## 3. Repository structure (Claude Code plugin best practice)

```
video-audio-agents/
├── .claude-plugin/
│   ├── plugin.json              # name, version, description, author, keywords; the engine MCP server (see §7)
│   └── marketplace.json         # this repo is its own marketplace (one plugin, source ".")
├── agents/
│   ├── transcriber.md
│   ├── translator.md
│   ├── voice.md
│   └── publisher.md
├── skills/
│   └── setup/
│       └── SKILL.md             # first-run setup Claude performs itself (standard or full)
├── engine/                      # the Python MCP server
│   ├── pyproject.toml
│   ├── uv.lock                  # committed: exact versions
│   ├── .python-version          # 3.11
│   ├── src/video_audio_engine/
│   │   ├── __init__.py
│   │   ├── server.py            # tool definitions only; each a few lines calling a module below
│   │   ├── paths.py             # output folders, free-name helper, data folder
│   │   ├── progress.py          # percent + message → MCP progress notification
│   │   ├── models.py            # which models exist, where they live, download with progress
│   │   ├── media.py             # fetch_media, list_links (yt-dlp)
│   │   ├── browser.py           # login pages: open in Edge/Chrome, catch the stream, export cookies
│   │   ├── transcribe.py        # faster-whisper; .txt + .segments.json
│   │   ├── subtitles.py         # .srt/.vtt from segments; burn-in
│   │   ├── clips.py             # cut, vertical crop, merge audio into video
│   │   ├── audio.py             # loudness, silence trim, music mix, podcast export
│   │   ├── texts.py             # save_text (translations, summaries, posts), search_texts
│   │   ├── voices.py            # save_voice, record_voice, list_voices, best-10-seconds sample
│   │   ├── speech.py            # speak, speak_timed, change_voice, tempo, pronunciation list
│   │   ├── speakers.py          # (Wave 2) who-said-what labels
│   │   └── setup_check.py       # check_setup
│   └── tests/
│       ├── unit/
│       ├── integration/         # real tools against a local HTTP server with media generated at test time
│       └── fixtures/            # one short public-domain speech WAV; everything else generated
├── docs/
│   ├── BUILD-PLAN.md            # this file
│   ├── USER-GUIDE.md            # plain English: install, first use, examples, troubleshooting
│   ├── adr/0001-python-engine-as-plugin.md
│   └── reference/               # (temporary) the two proven .pyw apps to port from
├── .github/workflows/ci.yml     # tests on windows-latest and ubuntu-latest
├── CLAUDE.md                    # rules for Claude Code in this repo (§14)
├── README.md                    # one-sentence install first, then examples and limits
├── CHANGELOG.md
├── LICENSE                      # MIT
└── .gitignore                   # engine/.venv, models, browser profiles, outputs
```

Per the Claude Code docs: `.claude-plugin/` holds only `plugin.json` and `marketplace.json`; `agents/` and `skills/` sit at the root. There is no root `.mcp.json` (§7 says why). Nothing generated or downloaded is committed.

---

## 4. The two waves

| | Wave 1 → release 1.0 | Wave 2 → release 1.1 |
|---|---|---|
| **Install & setup** | One-sentence install; setup skill (standard or full); Madav SDK check | GPU setup option; speaker-labels option |
| **transcriber** | Download video/audio/both from any link incl. login pages; transcript with timestamps or paragraphs; 3 accuracy levels; **subtitles (.srt/.vtt)**; **clean transcript, summary, key points, chapters, quotes, action items, study notes** (AI → saved files); **clips by time range**, optionally with burned-in subtitles | **Best-moment clips** (AI picks); **whole playlist/channel**; **search across all transcripts**; **audio clean-up** (even loudness, trim silence); **speaker labels** |
| **translator** | Translate transcript or any text; **translated subtitles**; glossary of fixed terms | **Bilingual side-by-side**; **simpler version** for learners; posts in the 6 languages |
| **voice** | Save voice (upload or record, with permission); speak text/transcript in a voice (6 languages); change the voice of an audio file; speed; **dubbing** (translated transcript → spoken in the original speaker's voice, in time → merged into the video) | **Narration** of scripts/blog posts/documents (podcast episode, audiobook); **intro/outro and background music**; **pronunciation list**; **podcast-ready export** (loudness, chapters) |
| **publisher** | From a transcript: **YouTube title options, description, tags, chapters**; **LinkedIn post, X thread, Instagram caption, hashtags, newsletter blurb**; **quote lines**; all saved as files | **Shorts/Reels package**: 3 best moments cut, subtitled, cropped vertical; **content calendar** (a week of posts from one video); **quote-card text** |
| **Engine** | CPU only; one model in memory; Windows first | **GPU when present**; **IndicF5** for Kannada/Tamil voice cloning; Mac verified; House-theme avatars for Madav's Agent Studio |

Wave 1 is complete on its own: paste a link, get the video, transcript, subtitles, summary, translation, dubbed version and a set of posts.

---

## 5. The engine: MCP tools (exact contracts)

Server name `engine`. Tool names: `mcp__plugin_video-audio-agents_engine__<tool>`. Agents allow the whole server with `mcp__plugin_video-audio-agents_engine__*`.

Every tool:
- returns a small JSON object as text, never prose;
- never overwrites: `name`, `name (2)`, `name (3)` … via `paths.free_path()`;
- reports progress with `ctx.report_progress(percent, 100, message)` at every ≥1% change, in plain words;
- stops cleanly on Esc (MCP cancellation): child processes killed, partial files removed, finished files kept;
- raises a one-sentence plain-English error with what to do next; tracebacks go to `${CLAUDE_PLUGIN_DATA}/engine.log`;
- downloads a model it needs if missing (with progress), so a tool never fails only because a model wasn't pre-fetched.

### Wave 1 tools

| Tool | Inputs | Output | Behaviour |
|---|---|---|---|
| `check_setup()` | — | `{ok, python, ffmpeg, deno, browser, models_present, models_missing_gb, free_ram_gb, free_disk_gb, gpu, notes}` | Fast, no downloads. Agents call it before heavy work and quote `models_missing_gb` when warning about a download. |
| `fetch_media(url, save, folder?)` | `save` ∈ audio / video / both | `{title, folder, files}` | yt-dlp `extract_info` first; if it fails, browser fallback (§6). audio → `bestaudio` + mp3; video → `bestvideo+bestaudio` merged mp4; both → keep both. `--no-playlist`. Creates `~/Documents/VideoAudioAgents/<title>/`. Progress from yt-dlp hooks. |
| `transcribe(file, accuracy, timestamps, delete_audio_after)` | accuracy ∈ fast / balanced / accurate (base / small / large-v3-turbo) | `{transcript_file, segments_file, language, lines, duration_seconds}` | `WhisperModel(..., device="cpu", compute_type="int8", cpu_threads=max(4, cores//2), download_root=DATA/models)` in `BatchedInferencePipeline`, `batch_size=8`. Writes `.txt` (timestamps `[12.5s] text` or paragraphs) **and** `.segments.json` (start, end, text) used by subtitles, clips and dubbing. Model cached per process. |
| `make_subtitles(segments_file, format, max_chars?)` | format ∈ srt / vtt | `{subtitle_file}` | Lines ≤ 42 chars, ≤ 2 lines, ≤ 6 s each. Works on translated segments too. |
| `cut_clip(video_file, start, end, subtitle_file?)` | times `mm:ss` or seconds | `{clip_file}` | ffmpeg stream copy when no subtitles; re-encode with burned-in subtitles when given. |
| `merge_audio_video(video_file, audio_file)` | | `{output_file}` | Replaces the video's audio track (dubbing). Pads or trims to the video length. |
| `save_text(next_to, label, text, ext, append_to?)` | ext ∈ txt / md / srt / json | `{file}` | Saves `name (label).ext` beside `next_to`, or appends. Used for translations, summaries, chapters, posts, glossary. |
| `list_voices()` | — | `{voices}` | From the voices folder. |
| `save_voice(source_file, name, consent)` | consent must be true | `{voice, sample_file}` | Trims silence, keeps ≤ 30 s. Refuses without consent. |
| `record_voice(name, seconds, consent)` | 10–30 s | `{voice, sample_file}` | Records the default microphone (`sounddevice`); refuses < 10 s of audio. |
| `speak(text?, transcript_file?, voice, language, speed, output_name?)` | language ∈ English / Kannada / Hindi / French / Spanish / Tamil; speed ∈ little_slower (0.9, default) / slower (0.8) / as_made (1.0) | `{output_file, seconds}` | Timestamps stripped. English → Chatterbox TTS; Hindi/French/Spanish → Chatterbox Multilingual; Kannada/Tamil → edge-tts reader (male/female by pitch of the sample) then `change_voice`. Sentence pieces ≤ 300 chars, 0.4 s pause. Tempo via ffmpeg `atempo`. |
| `speak_timed(segments_file, voice, language, speed)` | translated segments | `{output_file, overruns}` | **Dubbing:** speaks each segment and places it at the segment's start time so the new audio lines up with the video; speeds a piece up slightly (≤ 1.15×) when it would overrun, and reports the rest. |
| `change_voice(file, voice, speed)` | | `{output_file, seconds}` | Chatterbox VC in pieces ≤ 20 s cut at quiet moments; silence kept as silence. |

Shared rules in `speech.py`: one big model in memory at a time (voice / english / multilingual), freed before loading another; best 10 seconds of a saved voice chosen by loudness window, normalised to 0.9 peak.

### Wave 2 tools

| Tool | Inputs | Output | Behaviour |
|---|---|---|---|
| `list_links(url)` | playlist or channel link | `{links, titles}` | yt-dlp flat extraction; the agent then runs the normal flow per link. |
| `search_texts(query, folder?)` | | `{matches: [{file, line, text}]}` | Case-insensitive search across all transcripts. |
| `clean_audio(file, loudness, trim_silence)` | | `{output_file}` | ffmpeg `loudnorm` to −16 LUFS; silence trimmed at start/end. |
| `crop_vertical(video_file, focus?)` | focus ∈ center / left / right | `{output_file}` | 9:16 crop for Shorts/Reels, 1080×1920. |
| `mix_music(voice_file, music_file, music_volume, intro_file?, outro_file?)` | | `{output_file}` | Music ducked under the voice; intro/outro the user supplies. |
| `export_podcast(audio_file, chapters, title, artwork?)` | chapters from the transcript | `{output_file}` | mp3 at −16 LUFS with embedded chapter markers and tags. |
| `label_speakers(file, segments_file)` | | `{segments_file}` | Adds `speaker` to each segment (pyannote; needs a free Hugging Face token entered once via the setup skill). |
| `set_pronunciations(voice, pairs)` | `{"Madav": "Maa-dhuv"}` | `{count}` | Saved beside the voice; `speak` applies them. |
| GPU | — | — | `transcribe` and speech use `device="cuda"` when `check_setup` reports a usable NVIDIA GPU; CUDA torch installed by the setup skill on request. |
| IndicF5 | — | — | `speak` for Kannada/Tamil clones the voice directly (needs a transcript of the sample: the voice agent asks the person to read a short fixed sentence when saving a voice). |

---

## 6. Browser fallback (pages behind a login)

- Only when yt-dlp cannot read the link directly.
- Playwright with a persistent profile at `${CLAUDE_PLUGIN_DATA}/browser-profile`, so the login is remembered.
- Browser order: Edge → Chrome → Playwright's own Chromium (installed only when the setup skill is asked to, ~150 MB).
- Opens the page visibly, auto-plays `<video>` muted, captures the first `media` request or any `.m3u8`/`.mpd` URL, exports cookies to a temp Netscape file for yt-dlp (`--cookies`, `--referer`), deletes it afterwards.
- Waits up to 10 minutes for the first page (time to log in), 1 minute for the following ones in the same job.
- Never stores or prints credentials; the profile is private to the user.

---

## 7. Plugin wiring (verified against the Claude Code docs)

`.claude-plugin/plugin.json`, with the engine declared inline under `mcpServers` (`${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` are substituted in `command`, `args`, `env`):

```json
{
  "name": "video-audio-agents",
  "version": "1.0.0",
  "description": "Download, transcribe, translate, dub, voice and publish: four agents for video and audio links.",
  "author": { "name": "Madav", "url": "https://github.com/madavai" },
  "homepage": "https://github.com/madavai/video-audio-agents",
  "repository": "https://github.com/madavai/video-audio-agents",
  "license": "MIT",
  "keywords": ["transcribe", "youtube", "translate", "dubbing", "voice", "subtitles", "shorts", "social"],
  "mcpServers": {
    "engine": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--frozen", "--quiet", "--project", "${CLAUDE_PLUGIN_ROOT}/engine", "video-audio-engine"],
      "env": { "VAA_DATA": "${CLAUDE_PLUGIN_DATA}" },
      "timeout": 14400000
    }
  }
}
```

**Why not `.mcp.json` at the root:** Claude Code started inside the repo folder also reads a root `.mcp.json` as the project's own MCP config, where the two plugin variables are not substituted, so `engine` showed as failed ("Connection closed"). The manifest is read only when the folder is loaded as a plugin.

`.claude-plugin/marketplace.json`:

```json
{
  "name": "madavai",
  "owner": { "name": "Madav", "url": "https://github.com/madavai" },
  "plugins": [{ "name": "video-audio-agents", "source": ".", "description": "Download, transcribe, translate, dub, voice and publish agents." }]
}
```

Facts relied on: `mcpServers` in `plugin.json` takes inline servers keyed by name and is loaded together with any root `.mcp.json`, so the repo must not have one; `claude plugin validate .` checks the entry; `${CLAUDE_PLUGIN_DATA}` is created on first use, kept across updates, removed on uninstall unless `--keep-data`; `timeout` is a hard 4-hour limit per call (one link per call); progress notifications keep the 30-minute idle limit from firing; plugin agent files ignore `mcpServers`, `hooks`, `permissionMode`; the whole-server tool pattern ends in `__*`.

**Why `uv` is the command:** one small program, same on Windows and Mac, installs the pinned Python itself and the exact locked versions. The setup skill installs it. Phase 1 tests on Windows that Claude Code finds `uv` as `uv.exe`; if not, the command becomes the full path to `uv.exe` written by the setup skill.

---

## 8. Install, setup, and where models and binaries come from

**Users (README leads with this):** paste in Claude Code or Madav chat:

> Install https://github.com/madavai/video-audio-agents and set it up.

Claude runs `claude plugin marketplace add madavai/video-audio-agents`, then `claude plugin install video-audio-agents@madavai --scope user`, reloads, and runs the setup skill. The person approves once. Even if they say "clone", Claude installs it this way; no manual clone.

Claude desktop app (regular chat): Customize → Plugins → Add → paste `madavai/video-audio-agents` → Install, then "set up video audio agents". Developers: `git clone …` then `claude --plugin-dir .`.

### What gets downloaded, and from where

Nothing large is in the repo. The repo is code only (a few hundred KB). Everything below lands in `${CLAUDE_PLUGIN_DATA}` or the engine's private environment, with progress shown, and is reused forever after:

| Item | Size | Source | When |
|---|---|---|---|
| `uv` | ~15 MB | astral.sh installer | Setup, if missing |
| Python 3.11 (private copy) | ~30 MB | uv's managed Python | Setup, if missing |
| Packages incl. PyTorch CPU | ~2–3 GB | PyPI (pinned by `uv.lock`); ffmpeg and Deno come as PyPI packages too | Setup |
| Speech models `base`, `small` | ~150 MB + ~500 MB | Hugging Face (faster-whisper) | Setup |
| Speech model `large-v3-turbo` | ~1.6 GB | Hugging Face | First "accurate" job, or full setup |
| Chatterbox voice conversion | ~1 GB | Hugging Face (`ResembleAI/chatterbox`) | First voice job, or full setup |
| Chatterbox English TTS | ~2 GB | same repo | First English speech, or full setup |
| Chatterbox Multilingual | ~3 GB | same repo | First Hindi/French/Spanish speech, or full setup |
| Playwright Chromium | ~150 MB | Playwright | Only if no Edge/Chrome, on request |
| Wave 2: CUDA torch, pyannote, IndicF5 | 2–4 GB | PyPI / Hugging Face | `--gpu`, `--speakers`, `--indic` on request |

All model downloads go through `models.py`, one function: knows each model's name, size and location, downloads with progress into `${CLAUDE_PLUGIN_DATA}/models` (`HF_HOME` is pointed there so Chatterbox and faster-whisper share it), verifies the file exists and is complete before use, and resumes a broken download.

### Setup skill (`skills/setup/SKILL.md`)

Frontmatter `allowed-tools: Bash(uv:*), Bash(powershell:*), Bash(curl:*)`; uses `${CLAUDE_PLUGIN_ROOT}` to find the engine. Two modes:

- **Standard** ("set up video audio agents"): steps 1–4 below. About 3 GB. Enough for download, transcripts, subtitles, translation and posts.
- **Full** ("set up video audio agents with voice"): also pre-downloads the three Chatterbox models and `large-v3-turbo`. About 10 GB. Voice then works immediately with no wait on first use.

1. `uv --version`; if missing: Windows `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`.
2. `uv sync --frozen --project <plugin>/engine`.
3. `uv run --project <plugin>/engine video-audio-engine --warm standard|full` (downloads the models for the chosen mode, printing each name, size and progress).
4. States what was installed and the sizes, where files are saved, and reloads so `/mcp` shows `engine` connected.
5. On any failure: the exact error in plain words and the log path. Re-running setup is always safe; it skips what exists.

Wave 2 adds `--gpu` (CUDA torch), `--speakers` (Hugging Face token) and `--indic` (IndicF5) options.

Updates: GitHub marketplaces don't auto-update by default. README: "say *update video audio agents*" (Claude runs `claude plugin marketplace update madavai`, then setup again, which only installs what changed) or turn on auto-update under `/plugin` → Marketplaces.

Phase 1 confirms in MadavCC that Madav's chat (Agent SDK) sees plugins installed in the user's Claude folder; if it must be told, that is one setting in Madav, invisible to users.

---

## 9. The agents (full text to ship; Wave 2 sections are added in Wave 2)

Common frontmatter: `model: inherit`, `tools: Read, mcp__plugin_video-audio-agents_engine__*`. Never `mcpServers`, `hooks` or `permissionMode`.

### `agents/transcriber.md`

```markdown
---
name: transcriber
description: Downloads video or audio from links (YouTube, course pages behind a login, direct files), makes transcripts, subtitles, summaries, chapters and clips. Use when the person shares links or wants anything made from a video's words.
tools: Read, mcp__plugin_video-audio-agents_engine__*
model: inherit
---

You turn links into files: video (.mp4), audio (.mp3), transcript (.txt), subtitles (.srt/.vtt), notes and clips. The person may not be technical: short, plain messages; never show raw errors.

## Work out what they want
- Links: one or more. Keep: any mix of video, audio, transcript (default: audio + transcript).
- Accuracy: fast, balanced (default), accurate. Timestamps on by default.
- Extras they may ask for: subtitles, clean transcript, summary, key points, chapters, quotes, action items, study notes, a clip between two times.
Ask one short question only when something essential is unclear; otherwise use defaults and say which.

## Before heavy work
Call check_setup once. If it reports a problem, explain it in one line and stop. If a needed model is missing, say its size from models_missing_gb before starting.

## Each link, one at a time
1. fetch_media with save = "video" / "audio" / "both". If the engine says a browser window opened, tell them: "A browser window opened. Log in if asked (first time only) and press play if the video doesn't start."
2. Transcript wanted: transcribe the .mp3 (or the .mp4 if no .mp3). delete_audio_after = true only when they did not want the audio kept.
3. Subtitles wanted: make_subtitles from the segments file.
4. Notes wanted: Read the transcript, write the summary / key points / chapters (with mm:ss from the timestamps) / quotes / action items / study notes, and save each with save_text (labels: "summary", "chapters", "notes"…). A clean transcript: same words, no fillers, proper punctuation, label "clean".
5. Clip wanted: cut_clip with the times; add the subtitle file if they want captions.
If a link fails, say why in one line and continue. Every link has its own folder; nothing is overwritten.

## Finish
List the files per link (full paths) and any failures. If they also want a translation, dubbing, a voice or posts, hand over to translator, voice or publisher with the file paths.

## Wave 2
- A playlist or channel link: list_links first, then the normal flow per link; report progress per link.
- "Best moments": Read the transcript, pick up to 3 self-contained 30–60 s moments (a clear point with a hook), cut_clip each with subtitles; for Shorts also crop_vertical.
- "Where did he talk about X": search_texts and answer with file and time.
- "Clean up the audio": clean_audio. "Who said what": label_speakers before making notes.
```

### `agents/translator.md`

```markdown
---
name: translator
description: Translates transcripts, subtitles and texts into another language and saves them next to the original; prepares the text for dubbing. Use when the person asks for anything in another language.
tools: Read, mcp__plugin_video-audio-agents_engine__*
model: inherit
---

You translate faithfully and save the result. Short, plain messages.

1. Read the file. If it is already in the target language, say so and stop.
2. If the person has a glossary file (fixed terms, names), Read it and keep those terms exactly.
3. Translate in parts of about 150 lines. Keep every timestamp and the same line layout; do not summarise, shorten or "improve".
4. Save: save_text with label = the language name; first part without append_to, later parts with append_to set to the path returned.
5. Translated subtitles: translate the segments file the same way (text only, times unchanged), save it with ext "json", then make_subtitles from it.
6. Dubbing: produce the translated segments file (step 5), then hand over to the voice agent with that path and the video path.
7. Finish with the file paths. Offer a tone change (formal/informal) if they want.

## Wave 2
- Bilingual: original line, then translation, alternating; label "bilingual".
- Simpler version: same meaning in plain language for learners; label "<language> simple".
- Posts in the 6 languages: translate each post file the publisher made.
```

### `agents/voice.md`

```markdown
---
name: voice
description: Saves a person's voice (recorded or uploaded, with permission), reads text or transcripts aloud in that voice, dubs videos, and changes the voice in an audio file. Use for anything about voices, text-to-speech or dubbing.
tools: Read, mcp__plugin_video-audio-agents_engine__*
model: inherit
---

You work with voices. Short, plain messages.

## Permission first
Before saving any voice, ask: "Is this your own voice, or do you have the person's permission to use it?" Pass consent = true only if they confirm. Otherwise refuse politely and stop.

## Saving a voice
- Upload: save_voice with the file. Advise: quiet room, mic close, 20–30 s of natural speech, in the language they will mostly generate.
- Record: say you will record for N seconds (15–30) and that they should start speaking right after your next message, then record_voice.
- list_voices shows what exists.

## Before the first heavy use
check_setup. If voice models are missing, say the size (models_missing_gb) and that the first job downloads them once; voice needs about 6 GB of free memory and is slow on a normal PC (about 5–8 s of work per second of audio). Ask "go ahead?" before the first download. Mention that "set up video audio agents with voice" pre-downloads everything.

## Text to speech
speak with voice, language (English, Kannada, Hindi, French, Spanish, Tamil) and speed (little_slower by default). For a transcript pass transcript_file. Kannada and Tamil use a reader voice first and then convert, so the match is weaker; say so when relevant.

## Dubbing
Given a translated segments file and the video: speak_timed, then merge_audio_video. Tell them the dubbed video path, that timing follows the original speaker, and any overruns reported.

## Change the voice of an audio file
change_voice. Same words and timing; only the voice changes.

## Finish
Give the file path. If it does not sound right, suggest re-recording the sample (closer mic, quieter room) first.

## Wave 2
- Narration: a script, blog post or document → speak in parts; for an audiobook, one file per chapter plus the whole.
- Music: mix_music with the user's own music/intro/outro files; never fetch music from the internet.
- Pronunciations: set_pronunciations once per voice when they correct a name.
- Podcast export: export_podcast with chapters from the transcriber's chapters file.
- Kannada and Tamil cloning via IndicF5 when check_setup reports it installed; when saving a voice, ask the person to also read the fixed sentence shown.
```

### `agents/publisher.md`

```markdown
---
name: publisher
description: Turns a video's transcript into publishing material: YouTube title, description, tags and chapters; LinkedIn, X, Instagram and newsletter posts; quote lines; and (Wave 2) Shorts packages and a content calendar. Use when the person wants to share or promote a video.
tools: Read, mcp__plugin_video-audio-agents_engine__*
model: inherit
---

You write publishing material from a transcript. Short, plain messages. Everything is a draft the person edits; you never post anywhere.

## Inputs
The transcript (and chapters/summary if the transcriber made them). Ask for the platforms if not stated; default: YouTube + LinkedIn + X.

## Voice and rules
- Write in the speaker's own voice: their words, their examples, no hype, no invented facts or numbers.
- No clickbait; titles promise what the video delivers.
- One idea per post; a clear first line (the hook); a plain ending (what to do next).
- Hashtags: 3–5 relevant ones, lower case, at the end.

## What to make (save each with save_text, labels in brackets)
- YouTube: 5 title options ≤ 60 chars ["titles"]; description with a 2-line summary, chapters as mm:ss lines, and link placeholders ["description"]; 10–15 tags ["tags"].
- LinkedIn post, 150–250 words, line breaks between thoughts ["linkedin"].
- X thread, 5–8 posts ≤ 280 chars, numbered, first post stands alone ["x-thread"].
- Instagram caption ≤ 150 words + hashtags ["instagram"].
- Newsletter blurb, 80–120 words with a one-line subject ["newsletter"].
- Quote lines: 5 short exact quotes with mm:ss ["quotes"].

## Finish
List the files. Say they are drafts to review before posting.

## Wave 2
- Shorts package: ask the transcriber for the 3 best moments (subtitled, vertical); for each write a title ≤ 40 chars and a caption; save ["shorts"].
- Content calendar: 7 posts from one video, one per day, mixed platforms, each self-contained ["calendar"].
- Quote cards: the 5 quotes trimmed to fit a square card, one per line ["quote-cards"].
- Other languages: hand the post files to the translator.
```

---

## 10. Dependencies (pinned in `engine/pyproject.toml`, locked in `uv.lock`)

| Package | Purpose | Pin |
|---|---|---|
| `mcp` | MCP server (`from mcp.server.mcpserver import MCPServer`) | `>=2.3,<3` — 2.x renamed FastMCP → MCPServer; do not follow 1.x examples |
| `yt-dlp[default]` | downloads; `[default]` brings `yt-dlp-ejs` | latest at lock time, refreshed each release |
| `deno` | JS runtime yt-dlp needs for YouTube (PyPI package ships the binary) | latest |
| `static-ffmpeg` | ffmpeg/ffprobe binaries; engine adds them to PATH and passes `ffmpeg_location` | latest |
| `faster-whisper` | speech-to-text | `>=1.2,<2` |
| `huggingface-hub` | model downloads with resume (used by `models.py`) | as pulled by faster-whisper/chatterbox |
| `playwright` | browser fallback | `>=1.63,<2` |
| `chatterbox-tts` | voice cloning, TTS, voice conversion | `0.1.7` (pins torch 2.6.0) |
| `torch`, `torchaudio` | via chatterbox; CPU wheels from the PyTorch CPU index on Windows/Linux (`[tool.uv.sources]`); CUDA wheels as a Wave 2 extra | as chatterbox pins |
| `edge-tts` | Kannada/Tamil reader voices (online) | `>=7,<8` |
| `sounddevice`, `soundfile`, `librosa`, `numpy` | recording, audio I/O, analysis | compatible with chatterbox's pins |
| `mutagen` | mp3 tags and chapters (Wave 2) | latest |
| `pyannote.audio` | speaker labels (Wave 2, optional extra) | latest |
| dev: `pytest`, `jiwer` | tests, word-error-rate | — |

Python `3.11` (`.python-version`). Entry point `[project.scripts] video-audio-engine = "video_audio_engine.server:main"` with `--warm standard|full`, `--check`, `--gpu`, `--speakers`, `--indic` flags for the setup skill.

---

## 11. Testing

### Unit (every push)
`free_path` naming; transcript formatting; subtitle line splitting and timing; `text_pieces`; `cut_points` on synthetic audio; voice sample selection skips a quiet start; consent refusal; language → model routing; tempo mapping; `speak_timed` placement maths (no overrun beyond 1.15×); post length limits (X ≤ 280); `models.py` size table and "missing GB" arithmetic.

### Integration (CPU, tiny models, local HTTP server with media generated by ffmpeg at test time)
- fetch_media: direct mp3, direct mp4, HLS stream, same link twice → `(2)`, page without media → clear error, cancel midway → no partial files.
- transcribe: mp3 and mp4 with the `tiny` model on the bundled 10-second public-domain speech WAV → expected words present, both formats, `.segments.json` written, `(2)` on repeat, `delete_audio_after`.
- make_subtitles → valid .srt (timing monotonic, ≤ 42 chars/line); cut_clip with and without burn-in → duration ≈ requested; merge_audio_video → video length kept.
- save_text: create then append.
- models.py: a missing model is downloaded with progress and resumed after an interrupted download (simulated with a local server).
- MCP end-to-end: start the server over stdio with the Python MCP client, list tools, call check_setup, fetch_media, transcribe; assert progress notifications arrive.
- Wave 2: list_links on a generated local "playlist" page; clean_audio loudness within ±1 LU; crop_vertical → 1080×1920; export_podcast tags readable.

### Slow (local only, models present): `pytest -m slow`
save_voice, speak English one sentence, change_voice 10-second clip → output length ≈ input and speaker similarity ≥ 0.85 (Chatterbox voice encoder); speak_timed on 3 segments → each starts within 0.2 s of its time.

### CI (`.github/workflows/ci.yml`)
`windows-latest` and `ubuntu-latest`: install uv → `uv sync --frozen` → unit + integration (not `slow`). Cache the `tiny` model.

### Manual checklist (Chaithru, with screenshots)

Wave 1:
1. Paste the one sentence in Claude Code → ends with "Setup complete" and the sizes; `/mcp` shows `engine`. Repeat once in Madav.
2. YouTube link → video + audio + transcript + subtitles + summary + chapters.
3. Course link → browser opens; login remembered on the second run.
4. Transcript → Kannada translation; translated subtitles.
5. "Set up video audio agents with voice" → voice models downloaded; then save voice (upload) → speak English → speak Kannada.
6. Dub a 2-minute English clip into Hindi in the saved voice → plays in sync.
7. Clip 01:00–01:30 with captions.
8. Publisher: titles, description, LinkedIn post, X thread from one transcript.
9. Esc during a transcription → stops, no partial files.
10. Clone + `claude --plugin-dir .` → same agents.

Wave 2:
11. Playlist of 3 → 3 folders. 12. "Best moments" → 3 vertical subtitled Shorts. 13. Narrate a blog post with intro music → podcast mp3 with chapters. 14. "Where did he talk about X" → file and time. 15. Speaker labels on a two-person clip. 16. GPU PC: transcription ≥ 5× faster than CPU. 17. Kannada cloning via IndicF5 sounds closer than the reader route.

---

## 12. Phases (each ends with green tests and a PR)

### Wave 1 → release 1.0

| Phase | Builds | Done when |
|---|---|---|
| **1. Skeleton** | Repo structure, `plugin.json`, `marketplace.json`, `.mcp.json`, `pyproject` + `uv.lock`, `server.py` with `check_setup`, `models.py`, setup skill (standard/full), CI, README with the one-sentence install, CLAUDE.md; Madav SDK plugin check | One-sentence install works on Chaithru's PC; `/mcp` shows `engine`; `uv` launches on Windows; full setup downloads the models with progress |
| **2. Transcriber core** | `media.py`, `browser.py`, `transcribe.py`, `texts.py`, `transcriber.md` (download, transcript, notes) | Checklist 2, 3, 9, 10 |
| **3. Subtitles & clips** | `subtitles.py`, `clips.py` (cut, burn-in, merge) | Checklist 7; subtitles on item 2 |
| **4. Translator** | `translator.md`, translated subtitles, glossary | Checklist 4; a 1-hour transcript translates in parts without loss |
| **5. Voice & dubbing** | `voices.py`, `speech.py` (speak, speak_timed, change_voice), `voice.md`, slow tests | Checklist 5, 6; one model in memory at a time |
| **6. Publisher** | `publisher.md`, tests for limits | Checklist 8 |
| **7. Release 1.0** | USER-GUIDE, README final, CHANGELOG, ADR 0001, tag `v1.0.0`; fresh-PC install by one other person | Both installs work on a PC that never had Python |

### Wave 2 → release 1.1

| Phase | Builds | Done when |
|---|---|---|
| **8. Batch & search** | `list_links`, `search_texts`, `clean_audio`; transcriber Wave 2 section | Checklist 11, 14 |
| **9. Shorts & calendar** | best-moment picking, `crop_vertical`, publisher Wave 2 section, translator bilingual/simple/posts | Checklist 12 |
| **10. Narration & podcast** | `mix_music`, `export_podcast`, `set_pronunciations`, voice Wave 2 section | Checklist 13 |
| **11. Speakers & GPU** | `speakers.py`, `--speakers` and `--gpu` in the setup skill, CUDA path | Checklist 15, 16 |
| **12. IndicF5 & Mac** | Kannada/Tamil cloning (`--indic`), Mac verification, House-theme avatars for Madav's Agent Studio, tag `v1.1.0` | Checklist 17; checklist 1–10 pass on a Mac |

---

## 13. Risks and how the plan handles them

| Risk | Handling |
|---|---|
| yt-dlp breaks when sites change | Pinned but refreshed every release; "update video audio agents" upgrades it. |
| First-run download size (3 GB standard, ~10 GB full) | Setup names the sizes before starting; voice models only on request or first use. |
| A download is interrupted | `models.py` resumes; re-running setup is safe. |
| Slow on ordinary PCs | Batched, silence-skipped transcription; progress always visible; Stop always works; GPU in Wave 2. |
| MCP start timeout on first launch | Setup pre-installs everything; README says run setup first. |
| Dubbing timing drifts | `speak_timed` anchors every segment to its start time and caps speed-up at 1.15×; overruns are reported, not hidden. |
| Voice match disappoints | Best-10-seconds sample, speed control, re-record advice; IndicF5 in Wave 2. |
| Posts sound generic or invent facts | Publisher rules: speaker's own words, no numbers not in the transcript, drafts only. |
| Terms of use of sites | README: users are responsible for the sites' terms; the voice agent always asks consent. |
| Copy-protected services (Netflix etc.) | Clear error: not supported. |
| Memory (voice ~6 GB) | `check_setup` reports free RAM; one model in memory at a time. |

---

## 14. Proposed `CLAUDE.md` for the repo (shown for approval before it is written)

```markdown
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
```

---

## 15. Open questions for Chaithru

1. Agent names `transcriber`, `translator`, `voice`, `publisher`: fine, or Madav-style names?
2. Windows only for 1.0, with Mac verified in 1.1 (as planned), or Mac in 1.0 too (needs a Mac to test)?
3. Default folder `~/Documents/VideoAudioAgents/<title>/`: fine?
4. GitHub push access for the build session's pull requests: Settings → Connectors → GitHub → allow `madavai/video-audio-agents`.

---

## 16. Reference (Claude Code docs the plugin wiring follows)

- Plugin manifest: https://code.claude.com/docs/en/plugins/manifest-reference
- Marketplaces: https://code.claude.com/docs/en/plugins/marketplace-reference
- Installing plugins: https://code.claude.com/docs/en/plugins/install
- Plugin CLI (`--plugin-dir`): https://code.claude.com/docs/en/plugins/cli-reference
- MCP servers, timeouts, `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PLUGIN_DATA}`: https://code.claude.com/docs/en/mcp
- Subagents and tool patterns: https://code.claude.com/docs/en/sub-agents
- Skills and `allowed-tools`: https://code.claude.com/docs/en/skills
