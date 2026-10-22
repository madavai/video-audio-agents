# Video Audio Agents: user guide

Paste a link (or point at a recording on your computer) and say what you want: the video, the audio, a transcript,
subtitles, notes, a clip, a translation, a dubbed version in a saved voice, or posts to share it. Four helpers do the
work on your own computer:

| Helper | What it does |
|---|---|
| **transcriber** | downloads video and audio from links, makes transcripts, subtitles, notes (summary, chapters, quotes and more) and clips |
| **translator** | translates transcripts, subtitles and any text, keeping your fixed terms and names |
| **voice** | saves a voice (only with permission), reads text aloud in it, dubs a video into another language, changes the voice in a recording |
| **publisher** | writes YouTube titles, a description and tags, and LinkedIn, X, Instagram and newsletter drafts |

You don't call the helpers by name: ask in plain words and Claude hands the work to the right one. A request that
needs several ("dub this video into Hindi in my voice") runs them one after the other.

## Install

Paste this into Claude Code or Madav chat:

> Install https://github.com/madavai/video-audio-agents and set it up.

Claude adds the plugin and runs the setup. Claude Code asks you to allow each command; click allow. If Claude says
the setup isn't available yet, close Claude Code, open it again and say "set up video audio agents".

**Claude desktop app (regular chat):** Customize → Plugins → Add → paste `madavai/video-audio-agents` → Install.
Then say "set up video audio agents".

**Developers:** `git clone https://github.com/madavai/video-audio-agents`, then from that folder
`claude --plugin-dir plugins/video-audio-agents`, and say "set up video audio agents" once.

### What the setup downloads

The setup tells you the sizes before it starts, shows progress, and can be run again at any time: it skips what is
already there and continues a broken download.

| Setup | Size | What you can do straight away |
|---|---|---|
| "set up video audio agents" (standard) | about 3 GB | downloads, transcripts (fast and balanced), subtitles, clips, notes, translations, posts |
| "set up video audio agents with voice" (full) | about 10 GB | all of the above, plus accurate transcripts and voice work without a wait |

With the standard setup, the first accurate transcript downloads 1.5 GB more, and the first voice job downloads the
voice models (1 to 3 GB each). Claude tells you the size and asks before it starts.

The plugin's own files live in its data folder (`~/.claude/plugins/data/video-audio-agents-madavai/`): its private
copy of Python, ffmpeg (the video tool), the models, your browser logins and the log file. Nothing you make is kept
there.

## First use

1. **Restart Claude Code** after the setup (close it and open it again), so the engine starts. Type `/mcp`: `engine`
   should show as connected. If it shows as failed, choose `engine` there and pick **Reconnect**. (The engine can't
   start during the very first setup, and Claude Code may then leave it switched off for up to 15 minutes. If
   Reconnect doesn't help, wait 15 minutes and restart Claude Code again.)
2. **Ask for something**, for example:
   > Download the video and a transcript of https://www.youtube.com/watch?v=...
3. **Allow the engine's tools.** The first time a helper uses the engine, Claude Code asks whether to allow it.
   Choose the option that allows it from now on, so a long job isn't held up waiting for you.
4. **Watch the progress.** Long jobs show a percentage and what they are doing. Press **Esc** to stop at any time:
   finished files are kept and half-made ones are removed.
5. **Find your files** in `Documents/VideoAudioAgents/`, one folder per link, named after the video's title.
   Claude lists the full paths at the end.

Nothing is ever overwritten: asking again gives `<title> (2).mp3`, and so on.

## Download and transcribe (transcriber)

> Download the video of this lesson: https://...
>
> Audio and transcript of these two links, no timestamps.
>
> Transcript of this video with chapters and a summary.
>
> Accurate transcript of this talk, plus study notes and the key quotes.
>
> Subtitles for this video.
>
> Cut 01:00 to 01:30 out of this video, with captions.
>
> Transcript of the recording C:\Users\me\Videos\lesson.mp4.

What you get, for each link, in its own folder in `Documents/VideoAudioAgents/<title>/`:

| You ask for | File |
|---|---|
| video | `<title>.mp4` |
| audio | `<title>.mp3` |
| transcript | `<title>.txt`, one line per sentence with its time, like `[12.5s] ...` (or paragraphs, if you say "no timestamps") |
| summary, chapters, key points, quotes, action items, study notes | `<title> (summary).md`, `<title> (chapters).md`, ... |
| clean transcript (no "um"s, proper punctuation) | `<title> (clean).txt` |
| subtitles | `<title>.srt` (or `.vtt` for the web): at most 2 short lines, at most 6 seconds each |
| a clip | `<title> (clip 1-00 to 1-30).mp4`, or `... (captions).mp4` with the captions burned into the picture |

If you don't say what to keep, you get the audio and a transcript. A recording already on your computer works the
same way: its transcript and notes are saved next to it. To save downloads somewhere else, name the folder
("... and save it in D:\Lessons").

A `<title>.segments.json` file is also saved next to every transcript. It holds the timings that subtitles and
dubbing are made from; you can ignore it.

**Accuracy:** "fast", "balanced" (the default) or "accurate". Accurate is slower and downloads 1.5 GB the first
time.

**Notes** are written by Claude from the transcript, using only what was said: no invented facts or numbers.

**Clips:** without captions, a clip is made instantly, but it may start a second or two early (videos can only be
cut cleanly at certain frames). With captions it is re-made and starts exactly on time. Times past the end of the
video are cut back to the end.

**Pages behind a login (courses, members-only videos):** a browser window (Edge or Chrome) opens. Log in if asked
(only the first time; it is remembered) and press play if the video doesn't start. Leave the window open until the
download starts. You have 10 minutes to log in.

## Translate (translator)

> Translate it to Kannada.
>
> Kannada subtitles for this video.
>
> Translate the summary to Hindi.
>
> Always keep "process map" in English, and write Madav as ಮಾಧವ್.

You get `<title> (Kannada).txt` next to the transcript, line for line with the same times, and for subtitles
`<title> (Kannada).srt`. Any text (a summary, notes, posts) can be translated the same way. Translation is done by
Claude, so any language works.

Long transcripts are translated in parts and then checked line by line against the original, so no sentence is
skipped.

**Glossary:** names and terms you want kept a certain way are saved in `Documents/VideoAudioAgents/glossary.md` and
used in every translation. You can also edit that file yourself: one term per line, like
`process map → keep in English`.

## Voice and dubbing (voice)

> Save my voice from this recording: C:\Users\me\Desktop\me.m4a
>
> Record my voice.
>
> Read the summary aloud in my voice.
>
> Say "Welcome to the course" in Kannada in my voice.
>
> Dub this video into Hindi in my voice: https://...
>
> Change the voice in this recording to Anna's.

**Permission first:** a voice is only saved when it is yours, or the person agreed. Claude asks before saving one.

**Saving a voice:** give a recording of one person speaking (audio or video, 20 to 30 seconds of natural speech is
best), or say "record my voice": reply "ready" when asked and start reading anything aloud; recording starts when
you start speaking and lasts 20 seconds. For the closest match: a quiet room, the microphone close, in the language
you will mostly use. Voices are kept in `Documents/VideoAudioAgents/voices/` (one `.wav` per voice, at most 30
seconds).

**Languages:** English, Hindi, French and Spanish are spoken directly in the saved voice. Kannada and Tamil are
first read by a Microsoft reader voice (this needs the internet) and then changed into the saved voice, so they
sound less like it.

**Speed:** the voice models talk a little fast, so speech is made "a little slower" by default. Say "slower" for
learners, or "as made".

**Dubbing:** Claude downloads the video, makes a transcript, translates it (checked line by line, as for any
translation), speaks each translated sentence in the saved voice at the moment the original sentence started, and puts the new sound under the video:
`<title> (Hindi) (<voice> voice).mp4`. A sentence that is longer in the new language is sped up slightly (at most
15%) to fit; if one still runs over, Claude tells you where. Very short sentences are spoken together with the next
one, which sounds more natural.

What you get:

| You ask for | File |
|---|---|
| reading aloud | `<name> (<voice> voice).mp3` next to the file read; for text you typed, `<its first words> (<voice> voice).mp3` in `Documents/VideoAudioAgents/Speech/` (or a folder you name) |
| dubbing | `<title> (<language>) (<voice> voice).mp3` and the same name `.mp4` |
| a changed voice | `<name> (<voice> voice).mp3` next to the original |

**It is slow:** about 5 to 8 seconds of work per second of speech on an ordinary computer (dubbing a 2-minute clip
takes about 10 to 15 minutes), and it needs about 6 GB of free memory. Esc stops it at any time. One job can run for
at most 4 hours, so dub or read at most about 40 minutes at a time (ask for a clip of a longer video first). The
first voice job downloads the voice models (1 to 3 GB each) unless you set up "with voice".

Speech made by the voice models carries an inaudible watermark that marks it as made by AI.

## Titles, descriptions and posts (publisher)

> Write the YouTube titles, description, a LinkedIn post and an X thread for this video.
>
> An Instagram caption and a newsletter blurb for the lesson.
>
> Five quotes from the talk, with their times.

Make the transcript first (the transcriber does it from the link). If you don't name the platforms, you get
YouTube, LinkedIn and X. Everything is saved next to the transcript:

| You ask for | File | What's in it |
|---|---|---|
| YouTube titles | `<title> (titles).txt` | 5 options, each at most 60 characters (what YouTube shows in full) |
| YouTube description | `<title> (description).txt` | a 2-line summary, chapters with their times (starting at 00:00), and spots for your links |
| YouTube tags | `<title> (tags).txt` | 10 to 15 tags on one line, ready to paste |
| LinkedIn post | `<title> (linkedin).txt` | 150 to 250 words |
| X thread | `<title> (x-thread).txt` | 5 to 8 numbered posts, each within X's 280-character limit |
| Instagram caption | `<title> (instagram).txt` | at most 150 words, then hashtags |
| newsletter blurb | `<title> (newsletter).txt` | a subject line and 80 to 120 words |
| quotes | `<title> (quotes).txt` | 5 short quotes in the speaker's exact words, each with its time |

The posts use the speaker's own words and examples: no invented facts or numbers, and no clickbait titles. They are
drafts for you to read and edit; nothing is ever posted for you. Titles and X posts are checked for length when they
are saved, so they paste without being cut off. To get posts in another language, ask for a translation of the post
files.

## What stays on your computer

- Downloading, transcribing, subtitles, clips and voice work all run on your computer.
- The internet is used to download from the links you give, for the setup's downloads, and for the Kannada and Tamil
  reader voices (the text to be read goes to Microsoft's free reader service).
- Translations, notes and posts are written by Claude, so the transcript's text goes to Claude like anything else
  you share in the chat.
- Logins to course sites are kept in a private browser profile in the plugin's data folder; they are never shown or
  shared.

## Updating

Say "update video audio agents". Claude gets the new version, runs the setup again and asks you to restart Claude
Code. The engine, ffmpeg, the models and your browser logins are kept in the plugin's data folder, so an update only
adds what changed instead of starting over. You can also turn on automatic updates: `/plugin` → Marketplaces →
madavai.

## Uninstalling

Say "uninstall video audio agents". Claude removes the plugin and its data folder (the engine, the models and your
browser logins, up to 10 GB). Everything you made, in `Documents/VideoAudioAgents/`, stays.

## Limits

- Runs on your computer: Windows first. Mac is checked in version 1.1. Not available in claude.ai in a browser or on
  phones.
- Uses the processor only; using a graphics card to go faster comes in version 1.1.
- Copy-protected services (Netflix and similar) are not supported.
- You are responsible for following the terms of the sites you download from.
- Coming in version 1.1: whole playlists and channels, picking the best moments for Shorts, vertical clips,
  searching all your transcripts, audio clean-up, who-said-what labels, narration with intro music, podcast-ready
  files, and Kannada and Tamil spoken directly in the saved voice.

## Troubleshooting

- **`engine` isn't connected in `/mcp`, or Claude says the engine didn't start:** in `/mcp`, choose `engine` and pick
  **Reconnect**. Right after the first setup, Claude Code may leave the engine switched off for up to 15 minutes,
  because it couldn't start while the setup was still installing it: if Reconnect doesn't help, wait 15 minutes and
  restart Claude Code.
- **Claude says "run the setup":** say "set up video audio agents", then restart Claude Code. Running the setup again
  is always safe.
- **"Something went wrong":** the details are in `engine.log`, in the plugin's data folder
  (`~/.claude/plugins/data/video-audio-agents-madavai/`). Trying again usually works; if not, the log helps whoever
  looks at it.
- **A download stopped halfway:** ask again (or run the setup again). It continues where it stopped.
- **A link fails:** the other links still run. If a site that used to work stops working, say "update video audio
  agents": the downloader is updated with each release. Copy-protected services are not supported.
- **The login page opens but nothing downloads:** log in, then press play on the video, and leave the window open
  until Claude says the download has started.
- **No Edge or Chrome:** say "set up the login browser" to install one just for this (about 150 MB).
- **Wikipedia or Wikimedia Commons:** sound and video files download directly from the file's page or its file
  link; no browser window opens. The folder is named after the file (for example `Roosevelt Pearl Harbor`).
- **Claude keeps asking to allow the engine:** choose the option that allows it from now on; it is only asked once.
- **Voice work is very slow or stops for lack of memory:** close other large programs; voice needs about 6 GB of
  free memory. Try a shorter clip first.
- **The voice doesn't sound like you:** save a new sample: 20 to 30 seconds, closer to the microphone, in a quiet
  room, in the language you will use.
- **The dub drifts out of step in places:** Claude lists the lines that ran over. Ask for a shorter translation of
  those lines and dub again.
- **"The microphone couldn't be used" or "Nothing was heard":** check the microphone is plugged in and allowed in
  Windows Settings → Privacy & security → Microphone.
