# Changelog

## Unreleased (1.0.0)

### Phase 6: publisher
- New **publisher** agent: from a transcript (and its chapters or summary), drafts of YouTube title options, a description with chapters, tags, a LinkedIn post, an X thread, an Instagram caption, a newsletter blurb and quote lines with their times, each saved next to the transcript as `<name> (<label>).txt`. The speaker's own words, no invented facts or numbers, no clickbait; drafts only, never posted.
- `save_text` refuses a YouTube title over 60 characters (label `titles`) or an X post over 280 (label `x-thread`, counted the way X counts, emoji and Chinese as two), naming the one to shorten; nothing is saved until all fit. Added titles or posts are checked too.

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
