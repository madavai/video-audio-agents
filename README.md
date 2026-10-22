# Video Audio Agents

Paste this into Claude Code or Madav chat:

> Install https://github.com/madavai/video-audio-agents and set it up.

Then paste a link and get the video, the audio, a transcript, subtitles, notes, clips, a translation, a dubbed
version in a saved voice, and drafts of posts to share it. Four helpers for Claude Code, the Claude desktop app and
Madav, running on your own computer: free beyond your Claude or Madav subscription.

## Install

Claude installs the plugin, then runs the setup: about 3 GB of downloads, once. For voice and dubbing straight away,
say "set up video audio agents with voice" instead (about 10 GB). If Claude asks you to restart first, close Claude
Code, open it again and say "set up video audio agents".

**Claude desktop app (regular chat):** Customize → Plugins → Add → paste `madavai/video-audio-agents` → Install.
Then say "set up video audio agents".

**Developers:** `git clone https://github.com/madavai/video-audio-agents`, `cd video-audio-agents`, then
`claude --plugin-dir plugins/video-audio-agents` and say "set up video audio agents" once. The plugin itself is the
`plugins/video-audio-agents` folder; the rest of the repository (build plan, tests, CI) is for building it and is
not installed.

### For Claude: how to install this

When someone asks you to install this repository, do not clone it. Run:

1. `uv --version`. If uv is missing, install it first, so the engine can start as soon as the plugin is loaded:
   Windows `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, macOS or Linux
   `curl -LsSf https://astral.sh/uv/install.sh | sh`.
2. `claude plugin marketplace add madavai/video-audio-agents`
3. `claude plugin install video-audio-agents@madavai --scope user`
4. Then run this plugin's **setup** skill (standard, or full if they asked for voice). If the skill isn't available
   yet in this session, ask the person to restart Claude Code and say "set up video audio agents".

## What you can ask

**Downloads, transcripts, subtitles, notes and clips** (the transcriber)

> Download the video of this lesson: https://...
>
> Transcript of these two links, no timestamps, with chapters and a summary.
>
> Subtitles for this video. · Cut 01:00 to 01:30 out of it, with captions.

**Translations** (the translator)

> Translate it to Kannada. · Hindi subtitles for this video.

**Voices and dubbing** (the voice helper)

> Save my voice from this recording. · Read the summary aloud in my voice.
>
> Dub this video into Hindi in my voice.

**Titles and posts** (the publisher)

> Write the YouTube titles, description, a LinkedIn post and an X thread.

Everything for one link goes into its own folder in `Documents/VideoAudioAgents/`. Nothing is ever overwritten: a
second copy is saved as `name (2)`. The [user guide](docs/USER-GUIDE.md) has every example, what each one makes, and
what to do when something goes wrong.

## Updating

Say "update video audio agents". Or turn on auto-update: `/plugin` → Marketplaces → madavai.

## Limits

- Runs on your computer (Windows first; Mac is checked in version 1.1). Not available in claude.ai in a browser or
  on phones.
- Voice work needs about 6 GB of free memory and is slow on an ordinary computer (5 to 8 seconds of work per second
  of speech). English, Hindi, French and Spanish are spoken directly in the saved voice; Kannada and Tamil are read
  by an online reader voice first, so they match it less closely.
- Copy-protected services (Netflix and similar) are not supported.
- You are responsible for following the terms of the sites you download from. The voice helper only saves a voice
  that is yours or that you have permission to use.
- The helpers never post anything anywhere: posts are drafts for you to review.
- Coming in version 1.1: whole playlists, best-moment Shorts, search across transcripts, audio clean-up, speaker
  labels, narration with music, podcast files, graphics-card speed-up and Mac.

## Status

Version 1.0: Wave 1 of the [build plan](docs/BUILD-PLAN.md) is complete. See the [changelog](CHANGELOG.md) for
what changed, and [ADR 0001](docs/adr/0001-python-engine-as-plugin.md) for why it is built this way.

## Licence

MIT
