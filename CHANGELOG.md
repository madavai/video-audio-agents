# Changelog

## Unreleased (1.0.0)

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
