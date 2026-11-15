# Changelog

The version goes up with every change people should receive: a phase adds one to the middle number, a fix to the last. 1.0.0 is the release, after Phase 7.

## 1.5.2

### Fixes
- **Only the whole Kannada sentence is kept as a reading.** On the owner's PC with 1.5.1, a new reading of the
  sentence was accepted at 5.9 seconds, but it held only the first half, up to the comma (and its first syllable was
  clipped). Kannada spoken in the voice then began with the missing half ("ಉದ್ಯಾನವನಕ್ಕೆ ಹೋಗಿ ಸ್ವಲ್ಪ ಹೊತ್ತು ನಡೆ…") and
  lost the start of the words asked for. Two weaknesses together:
  - **The recorder stopped at the comma.** It stopped after 2 seconds of quiet, and people pause while reading an
    unfamiliar sentence. It now waits 5 seconds of quiet (at most 40 seconds in all), and keeps the 0.6 seconds
    before the first sound it starts on, so a soft first syllable isn't cut.
  - **The check let half a sentence through.** 1.5.1 kept a reading at least half alike to the sentence; a reading
    up to the comma is 0.54 to 0.63 alike. Now what speech recognition hears must be at least 0.7 alike, and at
    least half the letters of the sentence's last two words ("ಹೊತ್ತು ನಡೆಯೋಣ") must be heard in their place. A
    reading without them is refused in one sentence: "That recording stops before the end of the Kannada sentence,
    so it wasn't kept. Read the whole sentence again: pauses are fine."
  - A reading kept by 1.5.0 or 1.5.1 is checked the same way the first time it is used in a session: if it isn't
    the whole sentence, that Kannada is made with the reader voice, with a `note` saying why (it stops before the
    end, or other words were heard) and asking for the whole sentence again.
- **Pauses longer than a second are shortened to one second in a reading.** IndicF5 takes its pace from the
  reading: a reading with a 3-second pause made the owner's text 17% slower (6.9 seconds against 5.9), and a slow
  reader with a few pauses would have gone past the 15-second limit and been refused. Pauses of up to a second (the
  ones at "!" and ".") are kept as they are. With the pause shortened, the same reading was kept at 10.5 seconds
  and the text took 6.1 seconds.
- **Speech recognition listens to a reading in stretches of at most 10 seconds.** In one stretch it writes at most
  about 224 tokens, and in its usual 30-second stretches that cut the end off 9 of 24 FLEURS sentences by real
  Kannada speakers. The sentence takes 174, more when it is heard badly, so a real reading could have lost its last
  words and been refused. In 10-second stretches all 24 were heard to the end.
- The voice helper asks for the whole sentence, says pausing is fine, and gives the reason when a reading is
  refused.

### Tried for real
- **The owner's case, reproduced without the owner's microphone or voice.** A stand-in microphone played a Microsoft
  reader voice reading the sentence with a 3-second pause at the comma, through the real recorder, check and IndicF5,
  with the owner's text. With 1.5.1: the recording stopped at the pause, 5.9 seconds were kept and accepted, and the
  take (3.9 seconds) began "ಓಡ್ಯೋಗಿ ಸುಪೋತ್ತನ…", the missing "…ಹೋಗಿ ಸ್ವಲ್ಪ ಹೊತ್ತು ನ…", as the owner heard.
- **With 1.5.2:** the reading with the pause was recorded whole and kept, and the take said exactly the owner's text,
  in both reader voices. The fluent reading was kept as before, and its take was right too. The reading cut at the
  comma, with or without its first syllable, was refused with the new sentence. The half reading saved as 1.5.1
  would have: on first use its Kannada came from the reader voice, right, with the note "...stops before the end of
  the Kannada sentence. Read the whole sentence again...". No take had anything before the owner's words.
- **How well the check tells readings apart** (alike, and share of the last two words heard; speech recognition in
  10-second stretches): whole readings by two reader voices 0.92 to 0.97 and 0.75 to 0.92, with a 3-second pause
  too; stopped at the comma (with or without its first syllable) 0.54 to 0.63, the first 75% 0.63 to 0.74 and the
  first 90% 0.82 to 0.87, all with none of the ending; 24 FLEURS sentences by real speakers against their own words
  0.75 to 0.95 and 0.75 to 1.
- **The real model's test (`-m slow`)** also refuses the sentence read only up to its comma, and keeps a reading
  with a 3-second pause at the comma, shortened (passed, 344 seconds).

## 1.5.1

### Fixes
- **A Kannada reading is kept only if it is the sentence.** On the owner's PC, Kannada spoken directly in their voice
  began with "...ಹೊತ್ತು ನಡೆಯೋಣ" ("...walk for a while"), the end of the Kannada sentence, before the words asked for,
  and would have in every Kannada reading and dub in that voice. The cause: the saved "reading" wasn't the sentence
  at all, but 12.7 seconds of English talk the microphone picked up while it waited (speech recognition: English,
  certainty 1.0). IndicF5 is told the recording says the sentence; when it doesn't, the sentence's words that it
  can't place in the recording come out at the start of every take (of every part, in a long text: four times in
  a 40-second take). No way of preparing the recording can fix that, so the engine now listens first:
  - Saving a reading (`record_voice` or `save_voice` with `kannada_sentence`), the accurate speech-to-text model
    hears it with the language set to Kannada, and the reading is kept only if what it hears is at least half alike
    to the sentence, letter by letter. Otherwise it is refused in one plain sentence, and an earlier reading stays.
  - A reading saved by 1.5.0 is checked the first time it is used in a session: if it isn't the sentence, that
    Kannada is made with the reader voice, with a `note` asking for the sentence again. Each recording is listened
    to once per session (about 15 seconds on the processor).
  - "Set up the Kannada voice" now also downloads the accurate speech-to-text model (1.6 GB) if the full setup
    hasn't: only it writes Kannada (the fast and balanced models wrote readings of the sentence in Urdu or Hindi
    letters).
  - The voice helper asks for nothing else to be said near the microphone while the sentence records, and offers
    to record it again when a reading is refused or the note says so.
- **What it wasn't.** Three suspected causes were tried with the real model, and none was it: the reading's long
  pauses, the missing silence after it, and the sentence ending in "." without a space (F5 adds the space itself).
  Shortening the pauses and adding silence after the owner's reading still gave the leak, or lost the first word. A
  real reading of the sentence made as halting as the owner's (four pauses of 1.4 seconds, 12.7 seconds in all, cut
  tight at the end) gave the right words in all six takes, so the reading is used as before.

### Tried for real
- **The owner's text and reading.** "ನಮಸ್ಕಾರ! ಈಗ ನಾನು ನನ್ನದೇ ಧ್ವನಿಯಲ್ಲಿ ಕನ್ನಡ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ." with the owner's
  saved reading, on this PC with the real IndicF5: every take started with the sentence's last two to four words
  (speech recognition, large-v3-turbo), as the owner heard. The new check refuses that reading.
- **How well the check tells readings apart** (letters alike, 0 to 1; kept from 0.5): readings of the sentence by
  two Microsoft Kannada reader voices 0.92 to 0.97, fluent or halting; 24 sentences by two real FLEURS Kannada
  speakers against their own words 0.65 to 0.96; the first half of a reading 0.14 to 0.28; English speech (the
  owner's recording, and the tests' speech sample) 0. The fast and balanced speech models scored every Kannada
  reading 0, so only the accurate one can do this.
- **Readings of the sentence give the words asked for.** In the reader voices' readings, halting and fluent: the
  owner's text in six takes, a longer two-sentence text, and a 40-second text made in six parts. Every word was
  there, with nothing from the sentence, at the start of every part too.
- **The real model's test (`-m slow`, 171 seconds)** now also has a reader voice read another Kannada sentence (one
  that starts with the same "ನಮಸ್ಕಾರ") as the reading: it is refused, and the reading of the sentence is kept.
- **Checklist 17 is unchanged:** how IndicF5 makes speech from a kept reading didn't change, so its likeness and
  letter errors on the FLEURS speakers are the same as in 1.5.0.

## 1.5.0

Phase 12 (IndicF5 & Mac), the last part of Wave 2: Kannada spoken directly in a saved voice, Tamil unchanged, and
Mac readiness. Wave 2 is now complete except a first try on a real Mac, which waits until a Mac is at hand. The
release is 1.5.0 (the plan's `v1.1.0` was written before every phase raised the middle number).

### New
- **Kannada spoken directly in your saved voice: "set up the Kannada voice".** Before, Kannada was read by a Microsoft
  reader voice and then changed into the saved voice, which sounds only partly like the person. With this option,
  IndicF5 (AI4Bharat, IIT Madras: F5-TTS taught 11 Indian languages) speaks Kannada in the voice itself, for reading
  aloud, narration and dubbing. The default setup is unchanged. Tamil keeps the reader voice (the owner's choice),
  and IndicF5 is never downloaded or offered for it.
- **Its licence is in doubt, and the setup says so first.** IndicF5's makers publish it under the MIT licence, but
  their paper says it was made by further training F5-TTS's English model, whose weights are licensed for
  non-commercial use only (CC BY-NC 4.0, because of their training data). Another company that built on IndicF5
  released its model as non-commercial for that reason. The setup tells the person, before anything is downloaded,
  that it may be fine only for personal, non-commercial use, and asks whether to go ahead; the user guide and the
  voice helper say the same.
- **The model is gated on Hugging Face, handled like speaker labels.** The person accepts IndicF5's terms on its page
  themselves (Hugging Face then shares their account's name and email with AI4Bharat: the user guide says so), and
  the key goes only into the setup's small window, never into the chat or the log. One key serves both options: a
  key saved for speaker labels is used again, without a window. The model (1.4 GB, the voice model and its vocoder in
  one file, and its 11 KB list of letters) is pinned to an exact version and exact sizes and downloaded with progress
  and resume, like every model; F5-TTS never downloads anything itself.
- **A short Kannada sentence, read once for each voice.** IndicF5 copies a voice from a recording and the exact words
  said in it, so the engine keeps one fixed sentence (it means "Hello! This is my voice. The weather is lovely today,
  so let's go to the park this evening and walk for a while.") and the person reads it once: the voice helper shows
  it and records them (it stops 2 seconds after they stop), or takes a phone recording of them reading it. It is
  kept beside the voice as `<voice>.kannada.flac` (read again, it is replaced). Voices saved before: the first time
  Kannada is asked for in one, the voice helper offers the sentence; until it is read, or for a voice whose speaker
  can't be asked (one saved from someone else's video), Kannada keeps the reader voice.
- **It is slower than the other languages, and says so.** About 9 seconds of work per second of speech on the
  24-thread laptop it was tried on (F5's steps from noise to speech are 16, not its 32: measured to sound the same in
  half the time), so a 10-minute reading takes about an hour and a half; at most about 20 minutes of Kannada fit in
  one job. The voice helper says how long before a long Kannada reading or dub, the progress moves at each of
  IndicF5's steps (a take runs for minutes), and Esc stops it within seconds.
- **If IndicF5 can't be downloaded, Kannada still works.** When Hugging Face refuses the key (terms not accepted, a
  key it doesn't know) or the download drops, the Kannada is made with the reader voice, and one plain sentence says
  why and what to do.
- Engine: `indic.py` (IndicF5 built from its two files: F5-TTS's first "Base" design, `DiT(dim=1024, depth=22,
  heads=16, ff_mult=2, text_dim=512, conv_layers=4)`, and the Vocos 24 kHz vocoder; its notes go to the log, as
  stdout carries the MCP messages). `speak` and `speak_timed` return `route` (`direct` or `reader`) and, after a
  failed download, a `note`; `save_voice` and `record_voice` take `kannada_sentence`; `list_voices` returns
  `kannada_sentence` and `kannada_readings`; `check_setup` returns `kannada_voice`. Setup: `install.py indic`
  (optional extra `indic` = `f5-tts==1.0.8`, `datasets>=5`, `pyarrow<26`), `video-audio-engine --warm indic`.
  `models.GATED` names the setup to run for each gated model, so the key messages say "set up the Kannada voice" or
  "set up speaker labels".
- **Apple Silicon Macs (macOS 14 or later), ready but not yet tried on a real Mac.** Every package the engine uses has
  a ready-made build for these Macs; two of them (through faster-whisper) need macOS 14. The tests now also run on
  an Apple Silicon Mac on GitHub, on every change. The microphone messages name the Mac's own settings on a Mac; a
  file the Mac refused to open or save (the Documents folder not yet allowed) gets a plain message saying where to
  allow it, instead of "Something went wrong"; the setup says to open a new Terminal window after installing uv on a
  Mac; the key window comes to the front and takes the keyboard. `docs/MAC-TEST.md` is a plain-English list for
  whoever tries checklist items 1 to 10 on a Mac for the first time.

### Changed
- The `indic` extra moves five shared packages to the older versions the voice and speaker models were made with,
  for everyone (uv keeps one version of each package): filelock 4.2.4 → 3.32.7, fsspec 2026.9.0 → 2026.7.0,
  omegaconf 2.4.0 → 2.3.1, rich 15.0.0 → 13.9.4 and twine 7.0.0 → 6.2.0. Every test passes with them.
- **Cleaning up a recording cuts the silence at the end on a Mac too.** The Mac gets ffmpeg 7.0 (Windows and Linux
  8.0), which gives an mp3's length up to 0.08 seconds longer than its sound (it counts the encoder's delay at the
  start). The silence at the end was then not seen as running to the end, and was kept: a quiet recording lost 2.8
  seconds instead of 6.5. `clean_audio` now counts the length in the decoded sound (`astats`' number of samples),
  where the silence is found. Found by the first test run on a Mac.
- Why F5-TTS 1.0.8: 1.1.0 to 1.1.9 cap pydantic below what the MCP package needs, and later ones need torchcodec. Its
  trainer imports `datasets`, so the extra sets a floor on it (uv otherwise picked one from 2020) and keeps pyarrow
  below 26, which refuses NumPy 1 (the voice models need it).

### Not in this version
- Tamil spoken directly in the saved voice: by the owner's choice, Tamil keeps the reader voice.
- A first try on a real Mac (`docs/MAC-TEST.md` is ready for it), once a Mac is at hand.
- The House-theme avatars for Madav's Agent Studio: moved to after the build, together with the check in Madav (the
  owner's choice).
- The release tag and the GitHub release page.

### Tried for real
- **Kannada in a saved voice, checklist 17.** Two speakers from Google's FLEURS Kannada recordings (CC BY 4.0), a man
  and a woman, told apart by the speaker-voices model among the first 91 clips of its dev set. For each, an
  11-second clip and its own words stood in for the saved voice and the Kannada sentence, and six of their other
  sentences (6 to 14 seconds) were spoken by IndicF5 and by the reader route. Their real recordings were the
  yardstick: likeness by the speaker-voices model (wespeaker, from speaker labels; each real clip scores 0.91
  against the rest of the same person's clips, two different people about 0.05), and the words by speech
  recognition (faster-whisper large-v3-turbo in Kannada), as the share of letters it got wrong.
  - The woman: likeness 0.74 by IndicF5, 0.65 by the reader route; 6% of letters wrong, against 20%.
  - The man: 0.78 by IndicF5, 0.80 by the reader route, about the same; 8% of letters wrong, against 20%.
  - Speech recognition got 13% and 19% wrong on their real recordings: real reading has slips, pauses and room
    sound, so these figures compare the two routes; they don't rate the speech against a person.
  - Speed, on a laptop with an Intel Core Ultra 9 275HX (24 threads): F5's own 32 steps took 19 seconds of work per
    second of speech (16 to 21 for single sentences), 16 steps 9.1, with the same likeness (0.78 and 0.74, against
    0.77 and 0.76) and words (8% and 6% wrong, against 8% and 5%), so the engine uses 16. The reader route took 2.
- **The real model's test (`-m slow`, 96 seconds).** A Microsoft reader voice saved as the voice, with its reading
  of the sentence: IndicF5 spoke a new Kannada sentence at the length its words need, sounding like that voice and
  not like another Kannada reader voice. Esc part-way through a take stopped it there, and the next take came out
  right.
- **The setup with a real key.** The Kannada voice's install step on a developer data folder: the owner pasted their
  key into the key window (never into the chat or the log), Hugging Face let the download through once IndicF5's
  terms were accepted, the 1.4 GB model came down with progress, and check_setup then said `kannada_voice: true`.
  The copy of the key was deleted after the tries.
- **Through Claude with the plugin.** "Save speaker.wav as a voice called "FLEURS Kannada Test" ... keep sentence.mp3
  as that voice's Kannada sentence reading ... then read this aloud in that voice: ನಮಸ್ಕಾರ. ನಾಳೆ ಬೆಳಿಗ್ಗೆ ನಾವು
  ಮಾರುಕಟ್ಟೆಗೆ ಹೋಗೋಣ." (the FLEURS man's two clips, and the sentence said in his voice by IndicF5, as no recording of
  him reading it exists) went to the voice helper. It checked the setup, saved the voice, kept the reading
  (`save_voice` with `kannada_sentence`) and spoke the line directly (`route: direct`, 5 seconds, about 2 minutes
  20 in all with loading the model); speech recognition heard every word. The test files were deleted afterwards.
- **Tamil:** not tried, by the owner's choice; it works as before.

## 1.4.0

Phase 11 (Speakers & graphics card), the fourth part of Wave 2.

### New
- **Who said what.** "Who said what in this interview?" transcribes the recording as usual, then `label_speakers`
  finds who speaks when and saves a second transcript, `<name> (speakers).txt`, with the speaker on every line
  (`[12.5s] Speaker 2: ...`), and `<name> (speakers).segments.json` (each line with its `speaker`). Speakers are
  named Speaker 1, Speaker 2 and so on, in the order they first speak; a line where two people talk goes to the one
  who talks most of it; saying how many people speak helps. Claude says who each speaker probably is when the
  recording makes it clear (a name said or greeted). Notes of an interview, panel, podcast or meeting are written
  from this transcript, so they say who said what. Subtitles stay without names. It uses pyannote's speaker
  diarization 3.1 (the `pyannote.audio` package, 3.4.0, pinned) and runs on the processor.
- **Speaker labels are an option: "set up speaker labels".** The default setup is unchanged. The option installs
  pyannote (about 1 GB) and its three models (33 MB, pinned to exact versions and sizes, downloaded with progress
  and resume like every model). Two of the models are gated: the person makes a free Hugging Face account, accepts
  the terms on the two model pages and makes a "Read" key, all themselves (the setup lists the steps and the pages).
  The key is pasted into a small window that the setup opens, not into the chat, because the conversation keeps what
  is typed there. It is kept only in the plugin's private data folder and sent only to Hugging Face, only to download
  those two models; the server Hugging Face redirects the download to never gets it. If Hugging Face refuses, the
  message names what to do: accept the terms on the two pages it lists, or enter the key again (a key it doesn't
  know is forgotten, so the setup asks for it again).
- **Transcripts on an NVIDIA graphics card: "set up the graphics card".** The setup check names the card and
  suggests the option; it downloads NVIDIA's maths library (about 0.6 GB, 0.9 GB on disk), and from the next start
  transcripts run on the card, 13 to 24 times faster on the PC it was built on (see below), with the same words. If
  the card fails at some point, the same transcript is made on the processor and Claude says so in one line.
- **The setup check** reports the card's name (`gpu`), whether transcripts can use it (`gpu_usable`) and whether
  speaker labels are set up (`speaker_labels`), instead of "using it to go faster comes in a later version".
- **Setup options are remembered.** Running the setup again (after an update) keeps the graphics-card and speaker
  label options instead of removing them.
- **The transcriber's description and instructions** cover who said what, notes of conversations, and the
  graphics card.
- Engine tool `label_speakers(file, segments_file, people?)` in the new `speakers.py`; `gpu.py` (the card from
  `nvidia-smi`, NVIDIA's libraries found, the fallback); `transcribe` runs `float16` on the card. `models.SPEAKERS`
  (`pyannote/speaker-diarization-3.1` settings, `pyannote/segmentation-3.0`,
  `pyannote/wespeaker-voxceleb-resnet34-LM`),
  `models.GATED` and the key sent as an unredirected header. pyannote's checkpoints are opened with PyTorch's
  "weights only" check on, naming the four plain types they hold; the pipeline's 10-second windows move on every
  5 seconds instead of every second (`speakers.STEP`), which was 5.5 times faster and as right (see below). Setup: `install.py gpu` and `install.py speakers`
  (optional extras `gpu` = `nvidia-cublas-cu12==12.9.2.10` and `speakers` = `pyannote.audio==3.4.0`;
  `setup-options.json`), `video-audio-engine --warm speakers`.

### Not changed: voice stays on the processor
- Voice work (speaking, dubbing, changing a voice), the music keeper and speaker labels don't use the graphics card.
  They run on PyTorch, and the voice models (chatterbox-tts 0.1.7, the latest) require PyTorch 2.6.0 exactly.
  PyTorch 2.6 has no code for the newest cards: on this PC's RTX 5090 Laptop GPU (RTX 50 series) even a simple
  calculation fails ("no kernel image is available"); those cards need PyTorch 2.7 or later. Moving to it would
  break the voice models' pin, so the graphics-card option leaves PyTorch as it is.

### Fixed
- The 1.2.0 entry said the Shorts package on "Spectroscopy, Explained" took about 6 minutes; it took about 3½.

### Tried for real
- **Graphics card, checklist 16.** NASA Goddard's "Spectroscopy, Explained" (7 minutes 52 seconds) on an NVIDIA
  GeForce RTX 5090 Laptop GPU against the same PC's processor (the engine's 4 threads): "balanced" 4.5 seconds on
  the card against 57.9 on the processor (12.9 times faster), "accurate" 5.7 against 134.9 (23.7 times). With
  loading the model, 9.9 and 15.5 times. The two transcripts differ by one word in 1,075 (balanced) and none
  (accurate). A 54-minute NASA podcast episode took 34 seconds on the card.
- **Speaker labels, checklist 15.** Two episodes of NASA's "Houston We Have a Podcast" (public domain), each
  checked line by line against NASA's own transcript, which names who says every part. "ISS Results: Stem Cells in
  Space" (53 minutes 46 seconds, a host and a scientist): all 544 lines that match NASA's text have the right
  speaker. "ISS Results: Materials Science" (48 minutes 49 seconds, a host and two guests, found as three speakers
  without being told how many): 392 of 395 lines right, 99.7% of the talking time; the three misses are short
  thank-yous at the start and the end. About 5 minutes for each episode on the processor (24 threads), so about a
  minute for 10 minutes of sound. With pyannote's own setting (its 10-second windows moving on every second) the same
  episodes took 31 and 23 minutes, 95% of it in the voice model, with 542 and 392 lines right: moving every 5 seconds
  is what the engine now does. Through Claude with the plugin, "Who said what in this podcast?" on the Materials
  Science episode went to the transcriber, which checked the setup, transcribed on the card and labelled the
  speakers (8 minutes in all); the answer named the three people from what they say on the recording, with their
  talk times, and said the files keep Speaker 1, 2, 3. It also said 5 minutes "weren't assigned to anyone": those
  are pauses and music, so the transcriber's instructions now say every line has a speaker.

## 1.3.0

Phase 10 (Narration & podcast), the third part of Wave 2.

### New
- **Narration.** "Narrate this blog post in my voice" reads a text file (or text you give) aloud in a saved voice, in
  one piece when it takes under about 40 minutes to say and in parts when it is longer, saying first how long it will
  take. For an audiobook, each chapter is its own file; the whole book in one file is one more reading of all the
  text, so it takes as long as all the chapters again, and Claude asks first.
- **Your own music, intro and outro.** `mix_music` puts your music under a narration, with your intro before it and
  your outro after it (saved as `<narration> (with music).mp3`). Only files you give are used, never anything from
  the internet. The music plays all through the narration (a short piece repeats), turns itself down by about 15 dB
  while the voice speaks and comes back up in the pauses, and fades in and out. Every file is measured first, so the
  levels follow the voice and not how loudly each file was made: the intro and outro play as loud as the voice, the
  music at 0.4 of it in the pauses (8 dB under; say "quieter" or "louder"). Each try is a new file, so you can compare.
- **Podcast files.** `export_podcast` makes `<name> (podcast).mp3`: -16 LUFS (measured first, then written, as in
  `clean_audio`), 128 kbps, with the episode title, your own .jpg or .png as the cover picture, and chapter markers
  that podcast apps show, written into the file (ID3 tags, with the `mutagen` package, pinned). The chapters come
  from the transcriber's `<name> (chapters).md`: one line for each chapter, its time and its title. They must come
  from a transcript of the same audio (after any music is added), so Claude has the transcriber make it first; a
  chapter after the end of the audio, or two at the same moment, are refused. Nothing is uploaded or posted.
- **Names said right.** `set_pronunciations` teaches a voice how to say a word, written with hyphens ("Madav" →
  "Maa-dhuv"). The list is kept beside the voice (`<voice>.pronunciations.json`) and used by every reading and
  dubbing in that voice: whole words only, any case, "Madav's" too, and a word that only contains it ("Madavan") is
  left alone. Words already on the list are kept; a word with an empty respelling is taken off.
- **The voice helper's description and instructions** now cover narration, audiobooks, music, names and podcast
  files, and say that a podcast episode goes voice helper, transcriber, voice helper.
- **The graphics-card note** in the setup check no longer promises a version ("comes in a later version").
- **A project rule:** no Claude model name is written into the plugin; the four helpers stay on `model: inherit`.

### Fixed
- **Long sentences were read out of order.** When a sentence over 300 characters came after other sentences waiting
  to be spoken, it was spoken first. Quotations make such sentences common in stories: chapter 1 of a two-fable
  audiobook came out as "…the Lion laughed and let him go. The Mouse, recognizing his roar… to confer benefits on a
  *[then]* It happened shortly after this that the Lion was caught…", and speech recognition heard 32% of its words
  wrong. Reading aloud now keeps the order of the text (2.1% wrong).
- **A heading lost its last words.** A heading standing alone before a paragraph ("NASA Astronaut, STEM Creator
  Connect with Students for STEM Day.") was spoken without "for STEM Day". A short piece is now spoken together with
  the sentence after it, like short lines in dubbing.

### Tried for real
- **A podcast episode from a news article.** NASA's "NASA Astronaut, STEM Creator Connect with Students for STEM Day"
  (278 words, public domain) in the saved test voice Andrew, with an intro, a background piece and an outro that
  were made with ffmpeg for the test (nothing downloaded) and a generated cover picture. One plain request, "narrate
  this as a podcast episode called NASA STEM Day, with my music and cover and with chapters", ran the voice helper
  (it taught the voice "ClassCrunchLabs" and "CrunchLabs" first, read the article, mixed the music), then the
  transcriber (transcript of the finished audio, chapters), then the voice helper again (the podcast file): about 15
  minutes, almost all of it the voice reading. The 2 minute 23 second file has the title, the cover picture and 8
  chapters that ffmpeg's own reader lists in order, and measures -16.4 LUFS. Speech recognition on the narration
  alone got 97.9% of the words (the rest are how it spells "Menon", "Rober" and "Nov."), and 98.3% on the finished
  episode: the music does not cost a word, even when it is as loud as the voice in the pauses (music volume 1: still
  98.3%).
- **The music under the voice.** Measured on that narration (the music is what is left when the voice is taken out of
  the mix): at the default 0.4 it plays 21 dB under the voice while it speaks, at 0.7 16 dB and at 1.0 13 dB. The
  first try used 0.25, which was 32 dB under the voice, so faint that it would sound as if the music were missing,
  and the default was raised. Mixing 143 seconds of sound took 6 seconds; a second mix with another volume was saved
  as `(2)` and the first stayed.
- **An audiobook.** "Two Fables" (two chapters from a public-domain Aesop translation): one file for each chapter
  (49 seconds each) and the whole book (99 seconds, one more reading of all the text); speech recognition got 99.65%
  of the whole book's words.
- **Names.** The saved voice said "Madav" as "Madov" (heard as "Madov built this plugin"); after
  `{"Madav": "Maa-dhuv"}` it was heard as "Madhuv built this plugin".
- Found in these tries and fixed before release: the two reading problems above; the first default music level; and
  the chapters of a podcast were listed out of order by ffmpeg's reader whenever a long title came before a short
  one (the tag writer writes the smallest frames first; each chapter's name is now padded to one size). Stopping a
  podcast export with Esc just as ffmpeg finishes would have left a file without its tags; it is now removed too.

## 1.2.0

Phase 9 (Shorts & calendar), the second part of Wave 2.

### New
- **Shorts from a video's best moments.** "Make 3 Shorts from the best moments of this video" has the transcriber
  read the whole transcript and pick up to 3 moments of 30 to 60 seconds: each makes one clear point, makes sense
  without the rest of the video, and opens with a line that makes people want to hear more, in the speaker's own
  words. Each is made upright (1080 × 1920, the size YouTube Shorts, Instagram Reels and TikTok use) with the
  captions burned in, as `<title> (vertical 12-34 to 13-20) (captions).mp4`, and the moments are listed in
  `<title> (best moments).txt`. Ask for "the best moments" without Shorts and they come as ordinary clips with
  captions.
- **Captions that fit an upright screen.** Captions burned into the wide picture would lose both ends of every line
  when it is cut down to an upright one, so the picture is cut first and the captions are added afterwards: at most
  two short lines at a time, in large letters, above the spot where the apps show the title and buttons. The middle
  of the picture is kept; if the speaker stands to one side, ask for the left or right of the picture instead. For
  interviews, two people or text on screen, ask for the whole picture: it is shown in full across the middle on a
  blurred, enlarged copy of itself, so nobody is cut off (added after the real try, where the middle cut an
  interviewee framed to one side in half).
- **Shorts package.** The publisher writes a title (at most 40 characters, what a phone shows in full) and a caption
  with hashtags for each Short, saved as `<title> (shorts).txt`. A helper can't call another helper, so Claude runs
  the transcriber first (it makes the Shorts) and then the publisher.
- **A week of posts.** A content calendar: 7 posts from one video, one a day, mixing LinkedIn, X and Instagram (or
  the platforms you name), each making sense on its own day (`<title> (calendar).txt`).
- **Quote cards.** 5 quotes in the speaker's exact words, one per line, each at most 120 characters, ready to put on
  square images (`<title> (quote-cards).txt`). No images are made or downloaded.
- **Bilingual and simpler versions.** The translator makes a bilingual version (each line, then its translation
  under it: `<title> (Hindi bilingual).txt`) and a simpler version for learners (the same meaning in plain words,
  line for line with the same times: `<title> (Hindi simple).txt`, also in the transcript's own language).
- **Posts in other languages.** The translator turns each of the publisher's drafts into a post for that language's
  readers, saved next to it as `<title> (linkedin) (Hindi).txt` and so on, with the same length checks as the
  original.
- Engine tool `crop_vertical(video_file, focus, start, end, subtitle_file)`; `save_text` also checks Shorts titles
  (label "shorts", lines starting `Title:`, at most 40 characters), quote cards (at most 120) and a calendar's X
  posts (at most 280; in the real try one came out at 293), and a draft's translation saved next to it keeps the
  draft's limit (every label in the file's name counts).

### Tried for real
- NASA Goddard's "Spectroscopy, Explained" (7:52, one presenter at a desk): "Make a Shorts package from this video"
  had the transcriber pick 3 moments (42, 57 and 37 seconds) and make them upright with captions, then the publisher
  write their titles (33 to 36 characters) and captions, about 3½ minutes in all. The presenter stays in the picture,
  every caption is whole, and speech recognition on the Shorts hears each moment's first and last sentence in full.
  A 42-second Short took 9 seconds to make on 24 processor cores and 35 seconds on 4.
- From the same video: a 7-day calendar (LinkedIn, X and Instagram in turn), 5 quote cards (all the speaker's exact
  words), a bilingual English and Hindi transcript (77 of 77 lines), a simpler Hindi version, and the Shorts
  package and calendar in Hindi.
- NASA's "2016 Planetary Science Winter School" (3:28, interviews): 3 Shorts, then a whole Shorts package from the
  video on the computer, where Claude chose the whole-picture layout for the interview by itself.
- Found in these tries and fixed before release: one Short ended in 7 seconds of silent animation (moments now end
  half a second after their last sentence, not where the next one starts); a calendar's X post came out at 293
  characters (now checked); the middle cut showed only half of an interviewee framed to one side (the whole-picture
  layout); translations saved next to their draft escaped the length checks; and a wording in the transcriber's
  description stopped Claude Code from reading the helper's description at all (caught by the plugin check).

## 1.1.0

Phase 8 (Batch & search), the first part of Wave 2.

### New
- **Whole playlists and channels.** Give a playlist, a channel or a podcast feed and the transcriber reads the list
  first (nothing is downloaded yet), says its name and how many videos it has, then does each video in turn, exactly
  as for a single link, telling you after each one. The videos are kept together in
  `Documents/VideoAudioAgents/<playlist name>/`, one folder per video. A channel gives its videos, newest first (its
  Shorts and live streams only from a link to that tab). Lists with more than 50 videos are done 50 at a time, and
  Claude asks which ones first; a very big channel is counted up to 2,000 ("more than 2,000"; NASA's channel has
  over 5,500 videos). The videos are done one at a time: in the first try Claude started all of a playlist's
  downloads at once, which sites can block. Tried on a real YouTube playlist of 11 short videos (11 folders, each
  with its audio and transcript, in about 3 minutes) and on the first 3 videos of a 94-video playlist (3 folders, one
  video after the other).
- **Find where something was said.** "Where did he talk about X?" searches all your transcripts and answers with the
  video, the time and the sentence. It finds the lines with all the words searched for, in any order, capitals or
  not.
- **Clean up the audio.** A recording is brought to -16 LUFS, the loudness podcast apps and YouTube expect for
  speech, and the silence at its start and end is cut; saved as `<name> (clean audio).mp3` (a .wav stays a .wav). A
  video keeps its picture and its full length, with its sound evened out, as `<name> (clean audio).mp4`. It measures
  first and then writes, because measuring as it goes missed the loudness of short recordings by up to 8 LU; the
  result lands within 1 LU of -16. About a minute for every 15 minutes of sound (a 4½-minute talk took 15 seconds).
- Engine tools `list_links(url, start)`, `search_texts(query, folder)` and `clean_audio(file, loudness,
  trim_silence)`; the transcriber's description now names playlists, searching and clean-up, so Claude hands those
  requests to it.

## 1.0.3

### Fixes
- Dubbed videos keep the original music and sound effects; only the speaker's voice is replaced. Until now the dub replaced the video's whole sound, so the music was lost (found dubbing NASA's "Intro to Engineering" into Hindi: its intro and closing music were gone, and so was the soft music under the narrator). Now the video's own sound stays wherever nobody speaks, and under the dubbed sentences the original voice is taken out and the music plays on under the new voice at its original volume, with a short fade between the two. On that video, speech recognition hears no English left under the Hindi, and the intro, the closing music and the beeps at the end are kept as they were.
  - The voice is taken out by HTDemucs, the free music separator from the makers of Demucs (MIT licence): a 0.1 GB model downloaded once (with the voice models in the full setup, or on the first dub), pinned like the other models. It takes about as long as the video plays (2½ minutes for that 2¾-minute video on 4 processor cores) and about 2 GB of memory, after the voice model is let go.
  - `merge_audio_video` takes the dub's `segments_file` for this; without it the whole sound is replaced, as before (still used for changing the voice in a video).
  - The engine's pinned libraries now leave out Intel Macs, which PyTorch 2.6 already didn't support.
- The 1.0.1 notes below had lost their heading when 1.0.2 was added.

## 1.0.2

### Fixes
- Dubbing stays in step with the picture. In the release test, a 2:43 NASA video with a fast, nonstop narrator, dubbed into Hindi, fell up to 9 seconds behind: every line that ran long pushed all the lines after it later, and nothing let the dub catch up. Two causes were found and fixed:
  - The Hindi voice model now and then rambles on after a sentence, with made-up words or a few seconds of humming, or stops part-way (one take in five overall, and most takes on some sentences; one take dropped most of its sentence). The rambling always starts after a short silence where the words should end, so a take that runs far too long is now cut at that silence (checked by speech recognition on 33 such takes: every word kept, nothing extra), and a take that is still far too long or short is made again, up to three takes, keeping the best. This also fixes those garbled endings and lost words in reading aloud.
  - Some Hindi sentences simply take longer to say than the English ones. A translation for dubbing is now worded to be spoken: the translator checks each line against its time before anything is spoken (`translated_segments` with `dub_language`, from each language's measured speaking pace) and words the lines that wouldn't fit more shortly, keeping the meaning. It writes English words in the language's own script too, because the voice skipped a word written in English letters. This translation is saved as `<title> (Hindi dubbing).txt` and the dub as `<title> (Hindi dubbing) (<voice> voice).mp4`, so any other Hindi translation you have is never changed.
- The dub now reports how late its latest line starts (`most_late`), so Claude can tell you how closely it follows the original.
- A translated line saved again with the same time now replaces the earlier one, so single lines can be reworded.

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
