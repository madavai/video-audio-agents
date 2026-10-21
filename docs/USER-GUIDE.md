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

## Troubleshooting

- **"Run the setup"**: say "set up video audio agents". Running it again is always safe; it skips what is already there and continues broken downloads.
- **A link fails:** the other links still run. Copy-protected services (Netflix and similar) are not supported.
- **No Edge or Chrome:** say "set up the login browser" to install one just for this (about 150 MB).
- **Details of an error:** they are in `engine.log`, in the plugin's data folder (`~/.claude/plugins/data/video-audio-agents-madavai/`).
