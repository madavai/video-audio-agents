# Video Audio Agents

Paste a link, get the video, the audio, a transcript, subtitles, a translation, a dubbed version in your own voice, and posts to share it. Four agents for Claude Code, the Claude desktop app and Madav. Free beyond your Claude or Madav subscription: everything runs on your own computer.

## Install

Paste this into Claude Code or Madav chat:

> Install https://github.com/madavai/video-audio-agents and set it up.

Claude installs the plugin, then runs the setup (about 3 GB of downloads, once). For voice and dubbing straight away, say "set up video audio agents with voice" instead (about 10 GB).

**Claude desktop app (regular chat):** Customize → Plugins → Add → paste `madavai/video-audio-agents` → Install. Then say "set up video audio agents".

**Developers:** `git clone https://github.com/madavai/video-audio-agents`, then `claude --plugin-dir video-audio-agents`.

### For Claude: how to install this

When someone asks you to install this repository, do not clone it. Run:

1. `claude plugin marketplace add madavai/video-audio-agents`
2. `claude plugin install video-audio-agents@madavai --scope user`
3. Then run this plugin's **setup** skill (standard, or full if they asked for voice). If the skill isn't available yet in this session, ask the person to restart Claude Code and say "set up video audio agents".

## What you can ask

> Download the video of this lesson.
>
> Transcript of these two links, no timestamps, with chapters and a summary.
>
> Translate it to Kannada. · Dub it into Hindi in my voice.
>
> Make three Shorts from the best moments, with subtitles.
>
> Write the YouTube title, description, a LinkedIn post and an X thread.

Everything for one link goes into its own folder in `Documents/VideoAudioAgents/`. Nothing is ever overwritten: a second copy is saved as `name (2)`.

## Status

Being built in phases ([build plan](docs/BUILD-PLAN.md)). Done so far: the install, the setup and the engine's set-up check. The agents arrive in the next phases; see the [changelog](CHANGELOG.md).

## Updating

Say "update video audio agents". Or turn on auto-update: `/plugin` → Marketplaces → madavai.

## Limits

- Runs on your computer (Windows first; Mac in version 1.1). Not available in claude.ai in a browser or on phones.
- Voice work needs about 6 GB of free memory and is slow on an ordinary computer (5 to 8 seconds of work per second of audio).
- Copy-protected services (Netflix and similar) are not supported.
- You are responsible for following the terms of the sites you download from. The voice agent only saves a voice that is yours or that you have permission to use.
- The agents never post anything anywhere: posts are drafts for you to review.

## Licence

MIT
