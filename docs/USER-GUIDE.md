# Video Audio Agents: user guide

## Install

Paste this into Claude Code or Madav chat:

> Install https://github.com/madavai/video-audio-agents and set it up.

Claude installs the plugin and runs the setup: about 3 GB of downloads, once. Claude asks you to allow the setup commands; click allow. When it says so, restart Claude Code so the engine starts. Typing `/mcp` should then show `engine` as connected.

For voice and dubbing without waiting later, say "set up video audio agents with voice" instead (about 10 GB).

## Download and transcribe

Paste one or more links and say what you want. Examples:

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

A `<title>.segments.json` file is also saved next to every transcript. It holds the timings that subtitles and dubbing are made from; you can ignore it.

Nothing is ever overwritten: asking again gives `<title> (2).mp3` and so on.

**Clips:** without captions, a clip is made instantly, but it may start a second or two early (videos can only be cut cleanly at certain frames). With captions it is re-made and starts exactly on time. Times past the end of the video are cut back to the end.

**Accuracy:** "fast", "balanced" (the default) or "accurate". Accurate is slower and downloads 1.5 GB the first time.

**Pages behind a login (courses, members-only videos):** a browser window opens. Log in if asked (only the first time; it is remembered) and press play if the video doesn't start. Leave the window open until the download starts.

**Stopping:** press Esc. The job stops; files that were finished are kept, half-made ones are removed.

## Translate

> Translate it to Kannada.
>
> Kannada subtitles for this video.
>
> Translate the summary to Hindi.
>
> Always keep "process map" in English, and write Madav as ಮಾಧವ್.

You get `<title> (Kannada).txt` next to the transcript, line for line with the same times, and for subtitles `<title> (Kannada).srt`. Any text (a summary, notes, posts) can be translated the same way. Translation is done by Claude, so any language works.

Long transcripts are translated in parts and then checked line by line against the original, so no sentence is skipped.

**Glossary:** names and terms you want kept a certain way are saved in `Documents/VideoAudioAgents/glossary.md` and used in every translation. You can also edit that file yourself: one term per line, like `process map → keep in English`.

## Voice and dubbing

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

**Saving a voice:** give a recording of one person speaking (audio or video, 20 to 30 seconds of natural speech is best), or say "record my voice": reply "ready" when asked and start reading anything aloud; recording starts when you start speaking and lasts 20 seconds. For the closest match: a quiet room, the microphone close, in the language you will mostly use. Voices are kept in `Documents/VideoAudioAgents/voices/` (one `.wav` per voice, at most 30 seconds).

**Languages:** English, Hindi, French and Spanish are spoken directly in the saved voice. Kannada and Tamil are first read by a Microsoft reader voice (this needs the internet) and then changed into the saved voice, so they sound less like it.

**Speed:** the voice models talk a little fast, so speech is made "a little slower" by default. Say "slower" for learners, or "as made".

**Dubbing:** Claude downloads the video, makes a transcript, translates it, speaks each translated sentence in the saved voice at the moment the original sentence started, and puts the new sound under the video: `<title> (Hindi) (<voice> voice).mp4`. A sentence that is longer in the new language is sped up slightly (at most 15%) to fit; if one still runs over, Claude tells you where.

What you get:

| You ask for | File |
|---|---|
| reading aloud | `<name> (<voice> voice).mp3` next to the file read, or in `Documents/VideoAudioAgents/Speech/` |
| dubbing | `<title> (<language>) (<voice> voice).mp3` and the same name `.mp4` |
| a changed voice | `<name> (<voice> voice).mp3` next to the original |

**It is slow:** about 5 to 8 seconds of work per second of speech on an ordinary computer (dubbing a 2-minute clip takes about 10 to 15 minutes), and it needs about 6 GB of free memory. Esc stops it at any time. One job can run for at most 4 hours, so dub or read at most about 40 minutes at a time (ask for a clip of a longer video first). The first voice job downloads the voice models (1 to 3 GB each) unless you set up "with voice".

Speech made by the voice models carries an inaudible watermark that marks it as made by AI.

## Titles, descriptions and posts

> Write the YouTube titles, description, a LinkedIn post and an X thread for this video.
>
> An Instagram caption and a newsletter blurb for the lesson.
>
> Five quotes from the talk, with their times.

Make the transcript first (the transcriber does it from the link). If you don't name the platforms, you get YouTube, LinkedIn and X. Everything is saved next to the transcript:

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

The posts use the speaker's own words and examples: no invented facts or numbers, and no clickbait titles. They are drafts for you to read and edit; nothing is ever posted for you. Titles and X posts are checked for length when they are saved, so they paste without being cut off. To get posts in another language, ask for a translation of the post files.

## Troubleshooting

- **"Run the setup"**: say "set up video audio agents". Running it again is always safe; it skips what is already there and continues broken downloads.
- **A link fails:** the other links still run. Copy-protected services (Netflix and similar) are not supported.
- **No Edge or Chrome:** say "set up the login browser" to install one just for this (about 150 MB).
- **The voice doesn't sound like you:** save a new sample: 20 to 30 seconds, closer to the microphone, in a quiet room, in the language you will use.
- **"The microphone couldn't be used" or "Nothing was heard":** check the microphone is plugged in and allowed in Windows Settings → Privacy & security → Microphone.
- **Details of an error:** they are in `engine.log`, in the plugin's data folder (`~/.claude/plugins/data/video-audio-agents-madavai/`).
