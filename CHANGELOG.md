# Changelog

The version goes up with every change people should receive: a phase adds one to the middle number, a fix to the last. 1.0.0 is the release, after Phase 7.

## 1.0.1

### Fixes
- The engine now connects in the first restart after setup: no more waiting 15 minutes or pressing Reconnect. Before the setup has installed it, the engine starts as a small stand-in that connects straight away and only says to run the setup (or, once the setup is done, to restart), so Claude Code never sees it fail and never switches it off. The 1.0.0 advice to Reconnect or wait 15 minutes is gone from the setup's closing message and the user guide, except for one case: when the setup had to install uv, Reconnect may still be needed once.
- Claude's install steps in the README install uv first when it is missing, so the engine's command exists as soon as the plugin is loaded.

## 1.0.0

Release 1.0 (Phase 7): Wave 1 is complete. Paste a link, or point at a recording, and get the video, the audio, a transcript, subtitles, notes, clips, a translation, a dubbed version in a saved voice and drafts of posts, all made on your own computer by four helpers: the transcriber, the translator, the voice helper and the publisher.

### Release 1.0
- The user guide is complete: install, first use, every helper with examples and what each makes, what stays on your computer, updating, uninstalling, limits and troubleshooting.
- The README leads with the one-sentence install, then examples for each helper and the limits.
- The downloader (yt-dlp) is updated to its newest version (2026.10.21), as at every release, so sites that changed since August download again.
- A decision record (`docs/adr/0001-python-engine-as-plugin.md`) explains why the engine is Python inside a Claude Code plugin, and the five choices that changed during the build.
- The build plan now matches what was built; the two reference apps the engine was ported from are removed, as planned for the release.

### Fixes
- After the very first setup, a restart could still show the engine as not connected: the engine can't start while the setup is installing it, and Claude Code then leaves a server that failed switched off for up to 15 minutes (found while testing the release from GitHub). The setup's closing message and the user guide now say what to do: in `/mcp`, choose `engine` and pick Reconnect, or wait 15 minutes and restart.
- Dubbing could skip the check that no translated line is lost: asked to translate a timing file (`.segments.json`), the translator wrote the translated timing file itself instead of letting `translated_segments` build and check it (found dubbing a NASA video into Hindi; no line was lost that time). The translator now always translates the timestamped transcript next to it and lets `translated_segments` check it, which also keeps the times exactly as the engine wrote them.

## 0.6.0

Phase 5: voice and dubbing. All four agents are now in place; the 1.0 release (Phase 7) is next.

### Phase 5: voice and dubbing
- New **voice** agent: saves a voice (from a recording, or recorded on the computer's microphone) only with the person's permission, reads text and transcripts aloud in that voice, dubs a video into another language, and changes the voice in an audio or video file.
- `save_voice`, `record_voice`, `list_voices`: voices in `Documents/VideoAudioAgents/voices/`, the clearest 30 seconds of speech, never replaced. Recording starts when the person starts speaking, so no words are lost.
- `speak`: English, Hindi, French and Spanish in the saved voice (Chatterbox, on the computer); Kannada and Tamil read by a Microsoft reader voice and then changed into it. A little slower by default, as the models talk fast.
- `speak_timed` (dubbing): each translated line starts when the original line did; a line too long for its time is sped up at most 15%, and any that still run over are reported. `merge_audio_video` then puts it under the video.
- Dubbing speaks a very short line together with the next one, and trims the faint noise the voice models leave after the words: on a real NASA video, short Hindi lines spoken alone came out with babble after the words, long silences or a lost last word, which pushed the dub seconds out of step. Lines without words (a "…" over music) stay silent.
- `change_voice`: the same words and timing in another voice; silence stays silence.
- One big model in memory at a time: speech-to-text and the three voice models let each other go before loading, and a second voice or transcript job waits for the first to finish.
- The transcriber and translator hand over to the voice agent for dubbing.
- Speech made by the voice models keeps its inaudible watermark (a mark that it was made by AI), and voice work needs no internet except for the Kannada and Tamil reader voices. Two problems in the voice library stood in the way: the watermark didn't load without a small helper package, and the Hindi, French and Spanish model fetched a Chinese word list from the internet on every first load.

### Fixes
- The engine's log file (`engine.log`) stayed empty, although error messages point to it: the MCP SDK sets up logging first, which silently cancelled the engine's own setup.
- A clip without captions couldn't be cut from videos that carry a timecode track, as professionally exported videos often do (found on a NASA video). Clips now copy only the picture and the sound.

## 0.5.0

Phases 1 to 4 and 6. Voice and dubbing (Phase 5) come next, as 0.6.0.

### Packaging
- The version now follows the build. It said 1.0.0 from the start, and Claude Code only offers an update when the version changes, so nobody who installed early would ever have received a later phase.
- The plugin has its own folder in the repository, `plugins/video-audio-agents/` (agents, setup skill, engine), and the marketplace points there. Installing copies only that folder: no more build plan, reference apps, tests or CI files on people's computers. The engine's tests moved to `tests/` at the repository root. Developers load the plugin with `claude --plugin-dir plugins/video-audio-agents`.
- The engine's private Python (about 3 GB) is kept in the plugin's data folder (`venv`), no longer inside the installed plugin, which Claude Code replaces on every update. Run the setup once after updating to this version: it builds the engine there, mostly from files uv already has, then skips it on later updates.

### Phase 6: publisher
- New **publisher** agent: from a transcript (and its chapters or summary), drafts of YouTube title options, a description with chapters, tags, a LinkedIn post, an X thread, an Instagram caption, a newsletter blurb and quote lines with their times, each saved next to the transcript as `<name> (<label>).txt`. The speaker's own words, no invented facts or numbers, no clickbait; drafts only, never posted.
- `save_text` refuses a YouTube title over 60 characters (label `titles`) or an X post over 280 (label `x-thread`, counted the way X counts, emoji and Chinese as two), naming the one to shorten; nothing is saved until all fit. Added titles or posts are checked too.

### Fixes
- Opening Claude Code inside the repository folder no longer shows a failed `engine` server. The engine is now declared in the plugin manifest instead of a root `.mcp.json`; installing the plugin and `claude --plugin-dir` work as before.
- Download and transcript requests now go to the **transcriber** agent instead of being handled in the main conversation (its description says "Use proactively", like the translator's and publisher's). It also takes a recording already on the computer, and a folder to save into when one is named.
- Wikipedia and Wikimedia Commons file links (`…/wiki/Special:FilePath/…`, `…/wiki/File:…`, `upload.wikimedia.org`) now download instead of failing with "HTTP Error 403: Forbidden". Wikimedia turns away programs that pretend to be a browser, so the engine now names itself to Wikimedia sites only; every other site is downloaded exactly as before.
- A Wikipedia file page link (`…/wiki/File:…`, or `Datei:`, `Fichier:`… in other languages) names the folder and files after the file, as Commons does: `Roosevelt Pearl Harbor` instead of `FileRoosevelt Pearl Harbor.ogg - Wikipedia`.

### Phase 4: translator
- New **translator** agent: transcripts, notes and any text into another language, saved next to the original as `<name> (<language>).txt`; long transcripts in parts of about 150 lines.
- Translated subtitles: `translated_segments` pairs the translated lines with the original timings and refuses an incomplete translation, naming the missing lines, so nothing is lost; then `make_subtitles` makes `<name> (<language>).srt`.
- Glossary of fixed terms and names in `Documents/VideoAudioAgents/glossary.md`, kept exactly in every translation.
- `save_text` with an empty label saves under the given name (used for the glossary).
- Fixed: transcribing a recording longer than a few minutes crashed the engine on computers with many processor cores (found on a 24-core PC with a 40-minute lesson). Transcription now uses 4 threads, which was as fast.

### Phase 3: subtitles and clips
- `make_subtitles`: .srt or .vtt from a transcript or a translated one: at most 2 lines of 42 characters and 6 seconds per caption, nothing lost or reworded.
- `cut_clip`: a clip between two times, copied instantly, or with the captions burned into the picture.
- `merge_audio_video`: puts a new sound track under a video (used for dubbing), keeping the video's length.
- The transcriber agent makes subtitles and clips on request.
- Downloads now prefer mp4 files and convert other video formats to mp4 (some sites only offer .ogv or .webm).

### Phase 2: transcriber
- New **transcriber** agent: download video, audio or both from any link, transcripts, and notes (summary, chapters, key points, quotes, action items, study notes, clean transcript).
- `fetch_media`: YouTube and most video sites, direct file links, HLS streams, and pages behind a login (opens the page in Edge or Chrome and remembers the login). One folder per link; never overwrites; Esc removes half-made files; a dead link or a copy-protected video gets a plain message.
- `transcribe`: fast, balanced or accurate; one line per sentence with its time (or paragraphs), plus a `.segments.json` with the timings. Batched and silence-skipping for speed; word timings so no words are lost.
- `save_text`: saves what Claude writes next to the source, in parts for long texts; checks translated segments files.
- Setup can install a login browser on computers without Edge or Chrome.
- First version of the user guide.

### Phase 1: skeleton
- The plugin installs from this GitHub repository, which is also its own marketplace (`madavai`).
- The engine starts as the plugin's MCP server and answers `check_setup`: Python, ffmpeg, Deno, Edge or Chrome, which models are downloaded, how many GB each missing model needs, free memory and disk.
- The setup skill installs the engine and downloads ffmpeg and the models: standard (about 3 GB) or full with voice (about 10 GB), with progress, resuming a broken download.
- Tests run on Windows and Linux on every pull request.
