# Video Audio Agents: user guide

Paste a link (or point at a recording on your computer) and say what you want: the video, the audio, a transcript,
subtitles, notes, a clip, a translation, a dubbed version in a saved voice, or posts to share it. Four helpers do the
work on your own computer:

| Helper | What it does |
|---|---|
| **transcriber** | downloads video and audio from links (also whole playlists and channels), makes transcripts, subtitles, notes (summary, chapters, quotes and more) and clips, picks the best moments as clips or upright Shorts, finds where something was said, labels who said what, cleans up the sound |
| **translator** | translates transcripts, subtitles, posts and any text, keeping your fixed terms and names; makes bilingual and simpler versions for learners |
| **voice** | saves a voice (only with permission), reads text aloud in it (a narration, a podcast episode, an audiobook), adds your own music, intro and outro, makes podcast-ready files with chapters, learns how to say names, dubs a video into another language, changes the voice in a recording |
| **publisher** | writes YouTube titles, a description and tags, LinkedIn, X, Instagram and newsletter drafts, Shorts titles and captions, a week's content calendar and quote cards |

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

**On a Mac:** it needs an Apple Silicon Mac (M1 or later) with macOS 14 Sonoma or later; older Intel Macs can't run
the voice models' maths library. The first time, the Mac asks whether Terminal (or the Claude app) may use your
Documents folder, and later the microphone if you record your voice: click **Allow**. If the setup had to install
uv (the small program that runs the engine), close the Terminal window and open a new one (or quit the Claude app
with Cmd+Q and open it again) before restarting Claude Code. If your Documents folder is kept in iCloud Drive, the
videos you download are uploaded to iCloud too; name another folder if you'd rather they stay on the Mac. The Mac
is checked by tests on GitHub; [MAC-TEST.md](MAC-TEST.md) is the list for trying it on a real Mac.

### What the setup downloads

The setup tells you the sizes before it starts, shows progress, and can be run again at any time: it skips what is
already there and continues a broken download.

| Setup | Size | What you can do straight away |
|---|---|---|
| "set up video audio agents" (standard) | about 3 GB | downloads, transcripts (fast and balanced), subtitles, clips, notes, translations, posts |
| "set up video audio agents with voice" (full) | about 10 GB | all of the above, plus accurate transcripts and voice work without a wait |

With the standard setup, the first accurate transcript downloads 1.5 GB more, and the first voice job downloads the
voice models (1 to 3 GB each). Claude tells you the size and asks before it starts.

Three options are added only if you ask for them, after the standard setup:

| Option | Size | What it adds |
|---|---|---|
| "set up the graphics card" | about 0.6 GB (0.9 GB on disk) | transcripts on an NVIDIA graphics card, about 10 to 20 times faster ([more](#faster-transcripts-on-a-graphics-card)) |
| "set up speaker labels" | about 1 GB | who said what in interviews and conversations; needs a free Hugging Face account ([more](#who-said-what)) |
| "set up the Kannada voice" | about 1.7 GB (3.3 GB without the full setup) | Kannada spoken directly in your saved voice; needs a free Hugging Face account, and may be for non-commercial use only ([more](#kannada-in-your-own-voice)) |

Running the setup again later (after an update, for example) keeps the options you chose.

The plugin's own files live in its data folder (`~/.claude/plugins/data/video-audio-agents-madavai/`): its private
copy of Python, ffmpeg (the video tool), the models, your browser logins and the log file. Nothing you make is kept
there.

## First use

1. **Restart Claude Code** after the setup (close it and open it again), so the engine starts. Type `/mcp`: `engine`
   should show as connected. (Before the setup, the engine connects too, but can only tell Claude to run the setup.)
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

### Playlists and channels

> Transcripts of every video in this playlist: https://www.youtube.com/playlist?list=...
>
> Audio and transcripts of the latest 10 videos of https://www.youtube.com/@...

Claude first reads the list (nothing is downloaded yet) and tells you its name and how many videos it has. Then it
does each video in turn, exactly as for a single link, and tells you after each one ("Done 2 of 12: ..."). A video
that fails is skipped with the reason, and the rest carry on.

- The videos are kept together: `Documents/VideoAudioAgents/<playlist name>/<video title>/`.
- A channel link gives the channel's videos, newest first. Its Shorts or live streams come only if you give the
  link to that tab (`.../shorts`, `.../streams`).
- A list with more than 50 videos is done 50 at a time: Claude asks whether to do the first 50 or which ones. For a
  very big channel it says "more than 2,000" instead of counting to the end.
- Podcast feeds work too (an RSS link), and most video sites' playlists. A course page behind a login can't be read
  as a list: give its lessons' links one by one.
- A long list takes a long time: each video takes as long as it would on its own. Press **Esc** to stop; the videos
  that are done stay done.

### Find where something was said

> Where did he talk about inflation?
>
> When does she mention the deadline in the lesson videos?

Claude searches every transcript in `Documents/VideoAudioAgents/` (or the folder you name) and answers with the
video, the time and the sentence, for example: *"Lesson 3, at 12:40: 'Inflation is what happens when ...'"*. It
finds the lines that contain all the words it searches for, in any order, capitals or not, and tries other words
once if nothing turns up. Only videos with a transcript can be searched; transcripts without timestamps give the
sentence but no time.

### Clean up the audio

> Clean up the audio of my recording C:\Users\me\Recordings\talk.mp3.
>
> The sound of this video is too quiet. Fix it.

| You give | You get |
|---|---|
| an audio file | `<name> (clean audio).mp3` (the same kind of file: a .wav stays a .wav), at an even loudness, with the silence at the start and end cut (a third of a second is left) |
| a video | `<name> (clean audio).mp4`: the same picture, the sound at an even loudness, the same length |

"An even loudness" is -16 LUFS, the level podcast apps and YouTube expect for speech: a quiet recording becomes
louder, a loud one quieter, and the loudest moments stay clear of distortion. A video keeps its silence, because
cutting it would put the picture out of step; for a trimmed sound-only file, ask Claude to clean the video's .mp3.
You can also ask for only one of the two ("just cut the silence"). It takes about a minute for every 15 minutes of
sound. Claude tells you how loud it was before and how much silence was cut.

### Who said what

> Who said what in this interview?
>
> A transcript of this podcast episode with the speakers, and a summary.

Claude transcribes the recording as usual, then finds who speaks when and saves a second transcript next to the
first, `<title> (speakers).txt`, with the speaker on every line: `[12.5s] Speaker 2: ...`. The speakers are named
Speaker 1, Speaker 2 and so on, in the order they first speak. If the recording makes it clear who is who (someone
says their name, or is greeted by it), Claude tells you who each speaker probably is; the file keeps the numbers.
A line where two people talk goes to the one who talks most of it. Saying how many people speak ("the two people in
this interview") helps it tell them apart. It runs on the processor: about a minute for every 10 minutes of sound.

Notes (a summary, key points, chapters) of an interview, panel, podcast or meeting are written from the speakers'
transcript, so they say who said what. A recording with one speaker gets no labels. Subtitles stay without names.

**Setting it up (once):** say "set up speaker labels". The speaker models are free, but their makers (pyannote, on
the Hugging Face model site) ask everyone to accept their terms first, so you need your own free account there:

1. Make an account at https://huggingface.co/join (skip this if you have one).
2. Logged in, open https://huggingface.co/pyannote/segmentation-3.0 and accept the terms (approval is instant).
3. The same on https://huggingface.co/pyannote/speaker-diarization-3.1.
4. At https://huggingface.co/settings/tokens choose **Create new token**, the type **Read**, any name, then
   **Create**, and copy the key (it starts with `hf_`).

Claude then opens a small window: paste the key there and click **Save**. Don't paste it into the chat, because
the conversation keeps what you type. The key is kept only in the plugin's private folder on your computer and is
sent only to Hugging Face, only to download these two models (33 MB, once). If Hugging Face refuses it, Claude
says why (usually a page whose terms weren't accepted yet) and asks for the key again only if it was wrong.

### Faster transcripts on a graphics card

If your computer has an NVIDIA graphics card, the setup check says so. Say "set up the graphics card" (about
0.6 GB) and restart Claude Code: transcripts then run on the card. On an RTX 5090 laptop card, a 7 minute 52 second
NASA video took 4.5 seconds instead of 58 ("balanced") and 6 seconds instead of 2¼ minutes ("accurate"), with the
same words. If the card can't be used at some point (another program has filled its memory, for example), the
transcript is made on the processor as before and Claude says so in one line.

Voice work, dubbing and speaker labels stay on the processor: the voice models are built on a version of PyTorch
(the maths library they run on) that can't use the newest cards, such as the RTX 50 series.

### Best moments and Shorts

> Make 3 Shorts from the best moments of this video, with subtitles: https://...
>
> The best moments of the lesson as clips with captions.
>
> Make a vertical version of this video for Reels.

Claude reads the whole transcript and picks up to 3 moments of 30 to 60 seconds. Each one makes one clear point, makes
sense without the rest of the video, and starts with a line that makes people want to hear more (a question, a
surprising fact, a strong claim), in the speaker's own words. A short video may only have one or two.

| You ask for | File |
|---|---|
| the best moments | `<title> (clip 12-34 to 13-20) (captions).mp4` for each, with the captions burned in, plus `<title> (best moments).txt`: each moment's time, its point and its first sentence |
| Shorts, Reels, TikToks or "vertical" | `<title> (vertical 12-34 to 13-20) (captions).mp4` for each, upright (1080 × 1920, the size YouTube Shorts, Instagram Reels and TikTok use), plus the same list |
| a whole video made upright | `<title> (vertical).mp4` |

**How the upright picture is made:** the full height of the picture is kept and its middle is cut out (9:16). If the
speaker stands to one side, ask for "the left" or "the right" of the picture instead. For interviews, two people,
slides or text on screen, ask for "the whole picture": it is shown in full across the middle of the Short, on a
blurred, enlarged copy of itself, so nothing is cut off. The captions are added after
the picture is cut, in short lines of large letters sized for a phone, above the spot where the apps show the title
and buttons, so no caption loses its ends. Making a Short takes at most about as long as it plays (a 42-second
Short took 35 seconds on 4 processor cores, 9 seconds on 24).

To post them, ask the publisher for a Shorts package (below): a title and a caption for each Short.

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

> A bilingual English and Hindi version of the lesson.
>
> A simpler Hindi version for learners.
>
> Translate the posts into Kannada.

| You ask for | File | What's in it |
|---|---|---|
| bilingual | `<title> (Hindi bilingual).txt` | each line of the transcript with its time, then its translation under it, then a blank line: for reading along or learning |
| a simpler version | `<title> (Hindi simple).txt` | the same meaning in plain words and short sentences, line for line with the same times. In the transcript's own language too ("a simpler English version") |
| posts in another language | `<title> (linkedin) (Hindi).txt`, `<title> (x-thread) (Hindi).txt`, ... | each of the publisher's drafts, written as a post for that language's readers, not word for word, with the same length limits as the original |

A simpler version leaves out no point, name or number; it only says them more plainly. Subtitles can be made from it
like from any translation ("Hindi simple subtitles").

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

**Languages:** English, Hindi, French and Spanish are spoken directly in the saved voice. Kannada is too, once you
set up the Kannada voice ([below](#kannada-in-your-own-voice)). Tamil, and Kannada without that option, are first
read by a Microsoft reader voice (this needs the internet) and then changed into the saved voice, so they sound less
like it.

**Speed:** the voice models talk a little fast, so speech is made "a little slower" by default. Say "slower" for
learners, or "as made".

**Dubbing:** Claude downloads the video, makes a transcript, translates it (checked line by line, as for any
translation), speaks each translated sentence in the saved voice at the moment the original sentence started, and puts the new sound under the video:
`<title> (Hindi dubbing) (<voice> voice).mp4`. Most languages take longer to say than English, so the translation
for dubbing is worded to be spoken: the same meaning in shorter, plainer words, checked line by line so each sentence
can be said in the time the original took. It is saved as `<title> (Hindi dubbing).txt`, apart from any other
translation you have. A sentence that still comes out a little long is sped
up slightly (at most 15%) to fit. The voice model sometimes rambles on after a sentence (made-up words or humming):
that is cut off, and a sentence that comes out cut short is made again. If a sentence still runs over, the next one starts that much late and
catches up, and Claude tells you where. Very short sentences are spoken together with the next one, which sounds
more natural.

**The music stays:** only the speaker's voice is replaced. Wherever nobody speaks (an intro, a jingle, the music
between sentences, sound effects), you hear the video's own sound, untouched. Under the dubbed sentences, the
original voice is taken out of the sound and the music and sound effects play on under the new voice, at their
original volume. This uses a small music separator (0.1 GB, downloaded once with the voice models) and takes about
as long as the video plays. Anything said that isn't in the transcript, such as a countdown sung in an intro, stays
in the original language.

What you get:

| You ask for | File |
|---|---|
| reading aloud | `<name> (<voice> voice).mp3` next to the file read; for text you typed, `<its first words> (<voice> voice).mp3` in `Documents/VideoAudioAgents/Speech/` (or a folder you name) |
| dubbing | `<title> (<language> dubbing) (<voice> voice).mp3` and the same name `.mp4`, with the translation it speaks, `<title> (<language> dubbing).txt` |
| a changed voice | `<name> (<voice> voice).mp3` next to the original |
| narration with music | `<narration name> (with music).mp3` next to the narration, in stereo |
| a podcast episode | `<name> (podcast).mp3` next to the audio it is made from |
| an audiobook | `<book> - 1 <chapter> (<voice> voice).mp3` for each chapter, and `<book> - whole (<voice> voice).mp3` if you ask for it, in `Documents/VideoAudioAgents/Speech/` or the folder of the text |
| names said right | `<voice>.pronunciations.json` beside the voice's `.wav` |

**It is slow:** about 5 to 8 seconds of work per second of speech on an ordinary computer, plus about as long as
the video plays to keep a dub's music (dubbing a 2-minute clip takes about 12 to 17 minutes), and it needs about 6 GB
of free memory. Esc stops it at any time. One job can run for
at most 4 hours, so dub or read at most about 40 minutes at a time (ask for a clip of a longer video first).
Kannada in your own voice is slower still ([below](#kannada-in-your-own-voice)). The
first voice job downloads the voice models (1 to 3 GB each) unless you set up "with voice".

Speech made by the voice models carries an inaudible watermark that marks it as made by AI.

### Kannada in your own voice

> Set up the Kannada voice.
>
> Record the Kannada sentence for my voice.

Without this option, Kannada is read by a Microsoft reader voice and then changed into your saved voice, which sounds
only partly like you. With it, IndicF5, a speech model made by AI4Bharat at IIT Madras for Indian languages, speaks
Kannada directly in your saved voice. Tamil isn't part of it: Tamil keeps the reader voice.

**Before you set it up, two things to know:**
- **The licence may not allow commercial use.** IndicF5's makers publish it as free to use (the MIT licence), but
  they built it from another model, F5-TTS, whose makers allow only non-commercial use. So treat it as fine for
  personal, non-commercial use only; for videos you earn money from, check the licence first (or ask a lawyer).
- **Your name and email go to the model's makers.** IndicF5 is free but gated on Hugging Face: to download it, you
  accept its terms on its page, and Hugging Face then shares your account's name and email with AI4Bharat.

**Setting it up (once):** say "set up the Kannada voice". Claude tells you the two points above and asks before
anything starts. You need your own free Hugging Face account:

1. Make an account at https://huggingface.co/join (skip this if you have one).
2. Logged in, open https://huggingface.co/ai4bharat/IndicF5 and accept its terms (approval is instant).
3. If you haven't set up speaker labels: at https://huggingface.co/settings/tokens choose **Create new token**, the
   type **Read**, any name, then **Create**, and copy the key (it starts with `hf_`). Claude opens a small window:
   paste the key there and click **Save**, never into the chat. If you set up speaker labels before, the key you
   saved then is used again and no window opens.

It installs about 0.3 GB of programs and downloads the model (1.4 GB, once), and the accurate speech-to-text model
(1.6 GB) if the full setup hasn't already, then asks you to restart Claude Code.

**Reading one sentence, once for each voice:** IndicF5 copies a voice from a recording and the exact words said in
it, so each saved voice needs your reading of one short Kannada sentence. Claude shows it (it means "Hello! This is
my voice. The weather is lovely today, so let's go to the park this evening and walk for a while.") and records you
reading it once, at your normal pace; it starts at the first sound and stops by itself when you stop, so say nothing
else near the microphone until it stops (no talking to someone, no voice typing). A phone recording of you reading
it works too. Read it again any time to replace it. A voice saved before you set this up gets asked for the sentence
the first time you want Kannada in it; until then, or for a voice whose speaker you can't ask, Kannada keeps the
reader voice. The reading is kept beside the voice as `<voice>.kannada.flac`.

**Each reading is checked.** Because IndicF5 is told the recording says exactly that sentence, a recording of other
words makes it go wrong: it says the end of the sentence ("...walk for a while") before every text you give it. So
before a reading is kept, speech recognition listens to it (about 15 seconds), and a recording that isn't the
sentence is refused, with your earlier reading kept. A reading saved with version 1.5.0 is checked the first time
it is used: if it isn't the sentence, that Kannada is made with the reader voice, and Claude asks you to read the
sentence again.

**It is slower than the other languages:** about 9 to 10 seconds of work for each second of Kannada speech on the
computer it was tried on (24 processor threads), and longer on a computer with fewer. A one-minute reading takes
about 10 minutes, a 10-minute reading about an hour and a half, and dubbing a 2-minute clip into Kannada about 20
minutes. Claude says how long before it starts. The progress moves slowly, but it is working, and Esc stops it at any
time. One job can run for at most 4 hours, so read or dub at most about 20 minutes of Kannada at a time.

**If the model can't be downloaded** (its terms weren't accepted, the key was refused, or the internet dropped), your
Kannada is still made, with the reader voice, and Claude says why in one sentence.

### Narration, music and podcast files

> Narrate this blog post in my voice: C:\Users\me\Documents\post.txt
>
> Make an audiobook of this story, one file for each chapter and the whole book.
>
> Put my music under this narration, with my intro and outro: music.mp3, intro.mp3, outro.mp3.
>
> The voice says "Madav" wrongly. It should sound like "Maa-dhuv".
>
> Make this narration a podcast episode with chapters, called "Episode 1".

**Narration:** give the text as a file (plain text or Markdown) or type or paste it. Claude reads it in the saved
voice, in the language of the text (the languages above). A long text is read in parts, and Claude says first how
long it will take. For an audiobook, each chapter is its own file; the whole book in one file is one more reading of
all the text, so it takes as long as all the chapters again, and Claude asks first.

**Your own music:** only music files you give are used. Claude never looks for music on the internet. The music plays
all through the narration (a short piece repeats), turns itself down while the voice speaks, so every word stays
clear, and comes up again in the pauses; it fades in at the start and out at the end. Your intro plays before the
voice and your outro after it, as loud as the voice. You choose how loud the music is in the pauses ("quieter",
"louder"); how loud your files were made doesn't matter, because each is measured first. Every try is saved as a new
file (`... (with music).mp3`, then `... (with music) (2).mp3`), so you can compare them. It takes about a minute for
every 15 minutes of sound.

**Names:** if the voice says a name wrongly, tell Claude how it should sound, written with hyphens between the
syllables ("Madav" → "Maa-dhuv"). The list is kept with the voice (`<voice>.pronunciations.json` in the voices
folder) and used whenever that voice speaks, dubbing too, for that whole word in any case ("Madav's" as well). It only
counts for speech made after, so Claude reads the part again.

**A podcast file:** `<name> (podcast).mp3` has the loudness podcast apps expect (-16 LUFS), the episode title, your
cover picture if you give one (a .jpg or .png of your own; podcast apps like a square one, 1400 × 1400 pixels or
more) and the chapters written into the file, so apps show them. The chapters come from a transcript of the finished
audio, music included, so that their times fit: Claude has the transcriber make it and its chapters first, then the
voice helper makes the file. The podcast file takes about a minute for every 15 minutes of sound. Nothing is
uploaded or posted: you put the file on your podcast host yourself.

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
drafts for you to read and edit; nothing is ever posted for you. Titles, X posts, Shorts titles and quote cards are
checked for length when they are saved, so they paste without being cut off. To get posts in another language, ask
for a translation of the post files (the translator keeps the same limits).

### Shorts package, content calendar and quote cards

> Make a Shorts package from this video: https://...
>
> A week of posts from this video.
>
> Quote cards from the talk.

| You ask for | File | What's in it |
|---|---|---|
| a Shorts package | `<title> (shorts).txt`, with the Shorts themselves | for each of the 3 Shorts: its file and time, a title of at most 40 characters (what a phone shows in full) and a caption with hashtags, for YouTube Shorts, Instagram Reels or TikTok |
| a content calendar | `<title> (calendar).txt` | 7 posts, one a day (`Day 1 (LinkedIn)`, `Day 2 (X)`, ...), mixing the platforms; each makes sense on its own and takes a different idea from the video; the X days are checked against X's 280-character limit |
| quote cards | `<title> (quote-cards).txt` | 5 quotes in the speaker's exact words, one per line, each at most 120 characters, to put on square images |

**A Shorts package takes two helpers:** the transcriber picks the best moments and makes the upright Shorts with
captions, then the publisher writes their titles and captions. Claude runs them one after the other when you ask
for a Shorts package; if the Shorts already exist, only the publisher runs.

**Quote cards** are the words only: no images are made or downloaded. Put them on a square image in any design app
(Canva, PowerPoint...). A long quote is trimmed to a part of it that stands on its own, never reworded.

## What stays on your computer

- Downloading, transcribing, subtitles, clips and voice work all run on your computer.
- The internet is used to download from the links you give, for the setup's downloads, and for the Tamil and Kannada
  reader voices (the text to be read goes to Microsoft's free reader service). Kannada made by the Kannada voice
  option stays on your computer.
- Translations, notes and posts are written by Claude, so the transcript's text goes to Claude like anything else
  you share in the chat.
- Logins to course sites are kept in a private browser profile in the plugin's data folder; they are never shown or
  shared.
- Your Hugging Face key (only if you set up speaker labels or the Kannada voice) is kept in the plugin's data folder
  too. It is sent only to Hugging Face, to download those models, and never shown in the chat, the log or any file
  Claude makes.
- Setting up the Kannada voice shares your Hugging Face account's name and email with AI4Bharat, the makers of
  IndicF5, because its download page asks for them. Nothing else about you or your files is sent.

## Updating

Say "update video audio agents". Claude gets the new version, runs the setup again and asks you to restart Claude
Code. The engine, ffmpeg, the models and your browser logins are kept in the plugin's data folder, so an update only
adds what changed instead of starting over. You can also turn on automatic updates: `/plugin` → Marketplaces →
madavai.

## Uninstalling

Say "uninstall video audio agents". Claude removes the plugin and its data folder (the engine, the models, your
browser logins and your Hugging Face key, up to 12 GB). Everything you made, in `Documents/VideoAudioAgents/`, stays.
If you set up speaker labels or the Kannada voice, you can also delete the key on
https://huggingface.co/settings/tokens.

## Limits

- Runs on your computer: Windows, and Apple Silicon Macs with macOS 14 or later (checked by tests; a first try on
  a real Mac is still to come). Not available in claude.ai in a browser or on phones.
- Only transcripts use the graphics card, and only an NVIDIA one; voice work and speaker labels run on the processor.
- Copy-protected services (Netflix and similar) are not supported.
- You are responsible for following the terms of the sites you download from.
- Tamil is read by a reader voice and then changed into the saved voice, so it sounds less like you. Kannada
  spoken directly in the saved voice needs the Kannada voice option, whose model may be for non-commercial use only.

## Troubleshooting

- **`engine` isn't connected in `/mcp`, or Claude says the engine didn't start:** in `/mcp`, choose `engine` and pick
  **Reconnect**. This can happen once if the setup had to install uv (the small program that runs the engine): Claude
  Code tried the engine before uv was there, and waits up to 15 minutes before trying it again on its own.
- **Claude says "run the setup":** say "set up video audio agents", then restart Claude Code. Running the setup again
  is always safe.
- **"Something went wrong":** the details are in `engine.log`, in the plugin's data folder
  (`~/.claude/plugins/data/video-audio-agents-madavai/`). Trying again usually works; if not, the log helps whoever
  looks at it.
- **A download stopped halfway:** ask again (or run the setup again). It continues where it stopped.
- **A link fails:** the other links still run. If a site that used to work stops working, say "update video audio
  agents": the downloader is updated with each release. Copy-protected services are not supported.
- **A video in a playlist fails as private or removed:** its owner has hidden or deleted it; the rest of the list
  carries on.
- **A search finds nothing:** only videos with a transcript can be searched, and only the words actually said. Try
  another word, or the word in the language of the video.
- **The cleaned-up audio still sounds noisy:** clean-up evens out the loudness and cuts silence at the ends; it does
  not remove background noise or echo.
- **The login page opens but nothing downloads:** log in, then press play on the video, and leave the window open
  until Claude says the download has started.
- **Speaker labels: "Hugging Face won't share ... with this key yet":** log in on huggingface.co, accept the terms
  on the two pages the message names, then say "set up speaker labels" again. A key of the "Fine-grained" type also
  needs reading access to public gated models; a "Read" key has it.
- **Speaker labels: "didn't accept the saved key":** the key was mistyped or deleted on the site. Say "set up speaker
  labels" and paste a new one in the window.
- **Kannada: "made with the reader voice, because the Kannada voice model couldn't be downloaded":** your Kannada
  was still made. To get your own voice: log in on huggingface.co, accept the terms on
  https://huggingface.co/ai4bharat/IndicF5, then say "set up the Kannada voice" again (for a refused key, it asks for
  a new one).
- **Kannada sounds like the reader voice, not like you:** check the Kannada voice is set up, and that this voice has
  its reading of the Kannada sentence ("record the Kannada sentence for my voice").
- **Two people get the same label, or one person two:** say how many people speak ("label the two speakers"); very
  similar voices, or someone heard only for a word or two, can still be mixed up.
- **"The graphics card couldn't be used this time":** the transcript was made on the processor instead. Close other
  programs that use the card (games, video editors) and try again; restarting Claude Code tries the card again.
- **No Edge or Chrome:** say "set up the login browser" to install one just for this (about 150 MB).
- **Wikipedia or Wikimedia Commons:** sound and video files download directly from the file's page or its file
  link; no browser window opens. The folder is named after the file (for example `Roosevelt Pearl Harbor`).
- **Claude keeps asking to allow the engine:** choose the option that allows it from now on; it is only asked once.
- **Voice work is very slow or stops for lack of memory:** close other large programs; voice needs about 6 GB of
  free memory. Try a shorter clip first.
- **The voice doesn't sound like you:** save a new sample: 20 to 30 seconds, closer to the microphone, in a quiet
  room, in the language you will use.
- **The dub is out of step in places:** Claude lists the lines that ran over. Ask for a shorter wording of those
  lines and dub again.
- **A trace of the original voice can be heard under the dub:** the music separator works best on speech over music;
  with a very loud soundtrack, a faint trace may remain. Ask Claude to "put the dub under the video without the
  original sound" to replace the whole sound instead.
- **"The microphone couldn't be used" or "Nothing was heard":** check the microphone is plugged in and allowed in
  Windows Settings → Privacy & security → Microphone. On a Mac: System Settings → Privacy & Security → Microphone,
  switched on for Terminal (or Claude).
- **"The computer didn't allow a file to be opened or saved":** on a Mac, System Settings → Privacy & Security →
  Files and Folders, and allow Terminal (or Claude) to use the Documents folder. On Windows, close any program that
  has the file open.
