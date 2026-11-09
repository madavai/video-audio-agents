# Trying Video Audio Agents on a Mac

A short list for whoever tries the plugin on a Mac for the first time. It follows checklist items 1 to 10 of the
build plan (§11). For each step, note **OK** or what happened, with a screenshot of anything unexpected. Nothing here
needs any programming.

## Before you start

- **The Mac:** an Apple Silicon Mac (Apple menu → About This Mac shows "Chip: Apple M1" or later) with **macOS 14
  Sonoma or later**. Older Intel Macs can't run the voice models' maths library, so the plugin doesn't install there.
- **Space:** about 15 GB free.
- **Claude Code** installed and signed in, opened in Terminal (or the Code tab of the Claude app).
- **Chrome or Edge** in the Applications folder (for step 3).
- **A voice recording you may use:** your own voice, 20 to 30 seconds, or one whose owner agreed. Never someone
  else's voice without their permission.
- **A test video:** any public YouTube video of 3 to 10 minutes with clear speech (for example a NASA video), and a
  course page you can log in to (for step 3).

The Mac asks permission the first time something new is used. **Click Allow** each time:
- "Terminal (or Claude) would like to access files in your Documents folder": the results are saved in
  Documents/VideoAudioAgents.
- "... would like to access the microphone": only when you ask Claude to record your voice.

If you click Don't Allow by mistake: System Settings → Privacy & Security → Files and Folders (or Microphone), and
switch it on for Terminal or Claude.

## The steps

1. **Install.** Paste: *"Install https://github.com/madavai/video-audio-agents and set it up."* Click allow on each
   command. It should end with "Setup complete" and the sizes. If Claude says it installed uv, **close the Terminal
   window and open a new one** (or quit the Claude app with Cmd+Q and open it again), then start Claude Code. Type
   `/mcp`: `engine` should show as connected.
2. **A YouTube link.** *"Download the video of `<link>` with the audio, a transcript, subtitles, a summary and
   chapters."* Check the files in Documents/VideoAudioAgents/`<title>`/: the .mp4 plays, the transcript matches what
   is said, the subtitles show in QuickTime or VLC.
3. **A page behind a login.** *"Download the video of `<course lesson link>`."* A Chrome (or Edge) window opens: log
   in and press play if the video doesn't start. The video downloads. Ask again for another lesson: this time you
   aren't asked to log in.
4. **Translation.** *"Translate the transcript to Kannada, and make Kannada subtitles."* You get the `(Kannada).txt`
   and `(Kannada).srt` files.
5. **Voice.** *"Set up video audio agents with voice."* (about 7 GB more). Then *"Save my voice from `<recording>`.
   It is my voice."*, *"Say 'Welcome to the course' in English in my voice."* and the same in Kannada. Listen: it
   should sound like the saved voice. Also try *"Record my voice"* once, to check the microphone.
6. **Dubbing.** *"Cut the first 2 minutes of the video, then dub that clip into Hindi in my voice."* It takes about
   15 minutes. The dubbed .mp4 plays with the new voice in step with the lips, and the original music is kept.
7. **A clip.** *"Cut 01:00 to 01:30 out of the video, with captions."* The clip is 30 seconds and the captions are
   burned in.
8. **Posts.** *"Write the YouTube titles, description, a LinkedIn post and an X thread."* Four files, saved next to
   the transcript.
9. **Stopping.** Ask for an accurate transcript of a long video (over 20 minutes), and press **Esc** while it runs.
   It stops within a few seconds, and no half-made transcript is left in the folder.
10. **From a copy of the code** (for a developer): `git clone https://github.com/madavai/video-audio-agents`, then
    from that folder `claude --plugin-dir plugins/video-audio-agents` and *"set up video audio agents"*. The same four
    helpers work (repeat step 2).

Optional: *"Set up speaker labels"* (needs a free Hugging Face account; the guide lists the steps). A small window
opens for the key: click into it, paste with Cmd+V, click Save.

## If something fails

Send the step number, what Claude said, a screenshot, and the log file: in Finder press Cmd+Shift+G, paste
`~/.claude/plugins/data/video-audio-agents-madavai/engine.log`, and attach that file. It holds no passwords or keys.

## What is already known to differ on a Mac

- Transcripts, voice work and speaker labels run on the processor (Apple's graphics chips aren't used).
- If Documents is kept in iCloud Drive, downloaded videos are uploaded to iCloud too. To keep them only on the Mac,
  name another folder ("... and save it in my Movies folder").
