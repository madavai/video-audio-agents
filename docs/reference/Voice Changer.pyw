import asyncio, os, re, subprocess, sys, tempfile, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

OUT = r"C:\Audio"
VOICES = os.path.join(OUT, "voices")  # saved voices: one .wav per voice
os.makedirs(VOICES, exist_ok=True)
TITLE = "Voice Changer"
# The separate Python setup made by "Setup Voice Changer.bat", which has the voice tools installed.
PYTHON = os.path.join(OUT, "voice-env", "Scripts", "pythonw.exe")
NEEDS = ["chatterbox", "librosa", "soundfile", "edge_tts", "sounddevice"]
FIX = 'Double-click "Setup Voice Changer.bat" in C:\\Audio again, then reopen the Voice Changer.'


def start_up(python, needs, fix, log_name, title):
    """Makes the app start the same way every time, however it was opened."""
    import importlib.util
    missing = [m for m in needs if not importlib.util.find_spec(m)]
    # 1. Opened with a Python that lacks this app's helpers (double-clicking can pick the wrong one): reopen with the right one.
    if missing and os.path.exists(python) and not os.environ.get("AUDIO_TOOLS_REOPENED"):
        subprocess.Popen([python, os.path.abspath(__file__)], env={**os.environ, "AUDIO_TOOLS_REOPENED": "1"})
        sys.exit()
    if missing:
        box = tk.Tk()
        box.withdraw()
        messagebox.showerror(title, f"Some of this app's software is missing ({', '.join(missing)}).\n\n{fix}")
        sys.exit()
    # 2. Only one copy at a time: if it's already open, bring that window to the front instead.
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            globals()["_one_copy"] = kernel32.CreateMutexW(None, False, "AudioTools " + title)
            if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
                user32 = ctypes.WinDLL("user32")
                user32.FindWindowW.restype = wintypes.HWND
                window = user32.FindWindowW("TkTopLevel", title)
                if window:
                    user32.ShowWindow(window, 9)  # SW_RESTORE: un-minimize
                    user32.SetForegroundWindow(window)
                    sys.exit()
        except Exception:
            pass  # never let this check stop the app from opening
    # 3. There's no console window, so any output goes to a log file.
    sys.stdout = sys.stderr = open(os.path.join(OUT, log_name), "w", encoding="utf-8", buffering=1)

    # 4. A problem while starting shows a message, instead of nothing happening.
    def show_problem(kind, value, tb):
        import traceback
        traceback.print_exception(kind, value, tb)
        box = tk.Tk()
        box.withdraw()
        messagebox.showerror(title, f"{title} couldn't start:\n\n{value}\n\nDetails are in {sys.stdout.name}")
    sys.excepthook = show_problem


def bring_to_front():
    """Shows the window on top, even if Windows started it minimized or behind other windows."""
    root.deiconify()
    root.lift()
    root.attributes("-topmost", True)
    root.after(400, lambda: root.attributes("-topmost", False))
    root.focus_force()


start_up(PYTHON, NEEDS, FIX, "voice-log.txt", TITLE)

LANGUAGES = ["English", "Kannada", "Hindi", "French", "Spanish", "Tamil"]
# Languages the cloning model speaks directly in your voice (closest match).
CLONE_LANGS = {"English": "en", "Hindi": "hi", "French": "fr", "Spanish": "es"}
# The others: a free Microsoft voice reads the text first (male, female), then the voice is changed into yours.
READERS = {"Kannada": ("kn-IN-GaganNeural", "kn-IN-SapnaNeural"), "Tamil": ("ta-IN-ValluvarNeural", "ta-IN-PallaviNeural")}
# The speech model talks a little faster than people do; this slows the result without changing the pitch.
SPEEDS = {"A little slower": 0.9, "Slower": 0.8, "As made": 1.0}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
stop_flag = threading.Event()
loaded = {}  # holds at most one big model, so the PC keeps enough memory
recording = None


class Stopped(BaseException):
    """Raised when Stop is pressed."""


def check_stop():
    if stop_flag.is_set():
        raise Stopped()


def load_model(kind):
    """Loads a model when first needed, first releasing any other one (each takes several GB of memory)."""
    if kind not in loaded:
        import gc
        loaded.clear()
        gc.collect()
        if kind == "voice":
            say("Loading the voice model (the first time downloads about 1 GB)...")
            from chatterbox.vc import ChatterboxVC
            loaded[kind] = ChatterboxVC.from_pretrained("cpu")
        elif kind == "english":
            say("Loading the English speech model (the first time downloads about 2 GB)...")
            from chatterbox.tts import ChatterboxTTS
            loaded[kind] = ChatterboxTTS.from_pretrained("cpu")
        else:
            say("Loading the speech model for Hindi, French and Spanish (the first time downloads about 3 GB)...")
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            loaded[kind] = ChatterboxMultilingualTTS.from_pretrained("cpu")
    return loaded[kind]


def get_model():
    return load_model("voice")


def get_speech_model(language):
    """The cloning model: an English one, and one for Hindi, French and Spanish."""
    return load_model("english" if language == "English" else "multilingual")


def voice_sample(voice, folder):
    """The clearest 10 seconds of a saved voice, at an even volume (the models listen to 10 seconds)."""
    import librosa, numpy as np, soundfile as sf
    audio, sr = librosa.load(os.path.join(VOICES, voice + ".wav"), sr=24000)
    window = 10 * sr
    if len(audio) > window:  # slide a 10-second window and keep the part with the most speech
        hop = 512
        volume = librosa.feature.rms(y=audio, hop_length=hop)[0]
        frames = window // hop
        start = int(np.convolve(volume, np.ones(frames), "valid").argmax()) * hop
        audio = audio[start:start + window]
    peak = float(np.abs(audio).max()) or 1.0
    path = os.path.join(folder, "voice-sample.wav")
    sf.write(path, audio / peak * 0.9, sr)
    return path


def free_path(name, ext, folder=OUT):
    """A file name not used yet: "name.mp3", "name (2).mp3", ..."""
    name = re.sub(r'[\\/:*?"<>|]', "", name).strip()[:80] or "audio"
    path, n = os.path.join(folder, name + ext), 2
    while os.path.exists(path):
        path, n = os.path.join(folder, f"{name} ({n}){ext}"), n + 1
    return path


def cut_points(audio, sr, limit=20):
    """Where to cut long audio into pieces of at most `limit` seconds, preferring quiet moments."""
    import librosa
    loud = librosa.effects.split(audio, top_db=35)
    quiet = [(a[1] + b[0]) // 2 for a, b in zip(loud, loud[1:])]
    hop = 512
    volume = librosa.feature.rms(y=audio, hop_length=hop)[0]
    cuts, last = [0], 0
    while len(audio) - last > limit * sr:
        options = [q for q in quiet if last < q <= last + limit * sr]
        if options:
            last = options[-1]
        else:  # no pause found: cut at the quietest moment in the second half of the window
            lo, hi = (last + limit * sr // 2) // hop, (last + limit * sr) // hop
            last = (lo + int(volume[lo:hi].argmin())) * hop
        cuts.append(last)
    return cuts + [len(audio)]


def save_mp3(audio, sr, out_mp3, tempo=1.0):
    """Saves audio as .mp3, optionally slowed down (tempo below 1) without changing the pitch."""
    import soundfile as sf
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "all.wav")
        sf.write(wav, audio, sr)
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", wav]
        if tempo != 1.0:
            cmd += ["-filter:a", f"atempo={tempo}"]
        subprocess.run(cmd + [out_mp3], check=True, creationflags=NO_WINDOW)


def change_voice(source, sample, out_mp3, label, tempo=1.0):
    """Re-speaks `source` in the voice of `sample`, piece by piece, and saves an .mp3."""
    import librosa, numpy as np, soundfile as sf
    vc = get_model()
    vc.set_target_voice(sample)
    audio, sr = librosa.load(source, sr=16000)
    cuts = cut_points(audio, sr)
    pieces = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            check_stop()
            pct = i / (len(cuts) - 1) * 100
            say(f"{label}... {int(pct)}%", pct)
            if b - a < 0.3 * sr:  # too short to hold speech: keep it as silence
                pieces.append(np.zeros(int((b - a) / sr * vc.sr), dtype=np.float32))
                continue
            piece = os.path.join(tmp, f"{i}.wav")
            sf.write(piece, audio[a:b], sr)
            pieces.append(vc.generate(piece).squeeze(0).numpy())
        save_mp3(np.concatenate(pieces), vc.sr, out_mp3, tempo)


def clean_transcript(text):
    """Drops "[12.5s]" timestamps so they aren't read aloud."""
    lines = re.findall(r"(?m)^\[\d+(?:\.\d+)?s\]\s*(.*)$", text)
    return " ".join(lines) if lines else text.strip()


def text_pieces(text, limit=300):
    """Splits text into sentence-sized pieces of at most about `limit` characters."""
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.!?\u0964])\s+", text.strip()):
        while len(sentence) > limit:  # a very long sentence: split it at a space
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    return [p for p in pieces + [current] if p]


def clone_speech(text, language, sample, out_mp3, tempo):
    """Speaks the text directly in the voice of `sample`, piece by piece, and saves an .mp3."""
    import numpy as np
    tts = get_speech_model(language)
    tts.prepare_conditionals(sample)
    pieces = text_pieces(text)
    audio = []
    for i, piece in enumerate(pieces):
        check_stop()
        pct = i / len(pieces) * 100
        say(f"Speaking the text in your voice... {int(pct)}%", pct)
        if language == "English":
            wav = tts.generate(piece)
        else:
            wav = tts.generate(piece, language_id=CLONE_LANGS[language])
        audio += [wav.squeeze(0).numpy(), np.zeros(int(0.4 * tts.sr), dtype=np.float32)]  # pause between sentences
    save_mp3(np.concatenate(audio), tts.sr, out_mp3, tempo)


def reader_for(language, sample):
    """A male or female Microsoft reader, whichever is closer to the pitch of your voice."""
    import librosa, numpy as np
    audio, sr = librosa.load(sample, sr=16000)
    pitch = float(np.median(librosa.yin(audio, fmin=60, fmax=400, sr=sr)))
    male, female = READERS[language]
    return male if pitch < 165 else female


def speak(text, reader, out_mp3):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, reader).save(out_mp3))


def save_voice(audio, sr, name):
    """Stores up to 30 seconds of clean speech as voices/<name>.wav."""
    import librosa, soundfile as sf
    audio = librosa.effects.trim(audio, top_db=35)[0][: 30 * sr]
    path = free_path(name, ".wav", VOICES)
    sf.write(path, audio, sr)
    refresh_voices(os.path.splitext(os.path.basename(path))[0])


# ---------- the two jobs ----------

def run_job(job, *args):
    def work():
        try:
            out = job(*args)
            say(f"Done! Saved as {out}", 100)
            root.after(0, finish, out)
        except Stopped:
            say("Stopped.", 0)
        except Exception as e:
            say("Something went wrong.")
            root.after(0, lambda: messagebox.showerror("Error", str(e), parent=root))
        finally:
            root.after(0, set_busy, False)
    stop_flag.clear()
    set_busy(True)
    progress.set(0)
    threading.Thread(target=work, daemon=True).start()


def convert_job(source, voice):
    out = free_path(f"{os.path.splitext(os.path.basename(source))[0]} (in {voice} voice)", ".mp3")
    with tempfile.TemporaryDirectory() as tmp:
        change_voice(source, voice_sample(voice, tmp), out, "Changing the voice")
    return out


def speech_job(text, language, voice, title, tempo):
    out = free_path(f"{title} ({voice} voice)", ".mp3")
    with tempfile.TemporaryDirectory() as tmp:
        sample = voice_sample(voice, tmp)
        if language in CLONE_LANGS:
            clone_speech(text, language, sample, out, tempo)
        else:  # not spoken by the cloning model: a reader reads it, then the voice is changed
            say("Reading the text aloud...")
            plain = os.path.join(tmp, "speech.mp3")
            speak(text, reader_for(language, sample), plain)
            check_stop()
            change_voice(plain, sample, out, "Changing it into your voice", tempo)
    return out


# ---------- buttons ----------

def need_voice():
    if not voice_box.get():
        status.set("Record or upload a voice first.")
        return False
    return True


def need_permission():
    if not permission.get():
        messagebox.showinfo("Permission", "Tick the box to confirm this is your voice, or that the person agreed "
                            "to you using theirs.", parent=root)
        return False
    return True


def toggle_record():
    global recording
    import numpy as np
    if recording is None:
        if not need_permission():
            return
        import sounddevice as sd
        frames = []
        stream = sd.InputStream(samplerate=24000, channels=1, callback=lambda data, *_: frames.append(data.copy()))
        stream.start()
        recording = (stream, frames)
        record_button.config(text="Stop recording")
        status.set("Recording... Read anything aloud for 15 to 30 seconds in a quiet room, then click Stop recording.")
        return
    stream, frames = recording
    stream.stop()
    stream.close()
    recording = None
    record_button.config(text="Record my voice")
    audio = np.concatenate(frames)[:, 0] if frames else np.zeros(0, dtype=np.float32)
    if len(audio) < 5 * 24000:
        status.set("That was too short. Record at least 10 seconds of speaking.")
        return
    name = simpledialog.askstring("Name this voice", "Name for this voice:", initialvalue="My voice", parent=root)
    if name:
        save_voice(audio, 24000, name)
        status.set(f'Voice "{voice_box.get()}" saved.')


def upload_voice():
    if not need_permission():
        return
    path = filedialog.askopenfilename(title="Choose a recording of the voice",
                                      filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg"), ("All files", "*.*")])
    if not path:
        return
    name = simpledialog.askstring("Name this voice", "Name for this voice:",
                                  initialvalue=os.path.splitext(os.path.basename(path))[0], parent=root)
    if name:
        import librosa
        status.set("Saving the voice...")
        root.update()
        audio, sr = librosa.load(path, sr=24000)
        save_voice(audio, sr, name)
        status.set(f'Voice "{voice_box.get()}" saved.')


def choose_audio():
    path = filedialog.askopenfilename(title="Choose the audio to change",
                                      filetypes=[("Audio or video", "*.mp3 *.wav *.m4a *.flac *.ogg *.mp4"), ("All files", "*.*")])
    if path:
        audio_path.set(path)


def start_convert():
    if not audio_path.get():
        status.set("Choose an audio file first.")
    elif need_voice():
        run_job(convert_job, audio_path.get(), voice_box.get())


def open_transcript():
    path = filedialog.askopenfilename(title="Choose a transcript", filetypes=[("Text", "*.txt"), ("All files", "*.*")])
    if path:
        with open(path, encoding="utf-8") as f:
            text_box.delete("1.0", "end")
            text_box.insert("1.0", clean_transcript(f.read()))
        transcript_title.set(os.path.splitext(os.path.basename(path))[0])


def start_speech():
    text = clean_transcript(text_box.get("1.0", "end"))
    if not text:
        status.set("Type, paste or open some text first.")
    elif need_voice():
        run_job(speech_job, text, language_box.get(), voice_box.get(), transcript_title.get() or "Speech",
                SPEEDS[speed_box.get()])


def stop():
    stop_flag.set()
    stop_button.config(state="disabled")
    status.set("Stopping... (finishing the current small piece)")


# ---------- window helpers ----------

def say(msg, pct=None):
    root.after(0, status.set, msg)
    if pct is not None:
        root.after(0, progress.set, pct)


def set_busy(busy):
    for b in (convert_button, speech_button, record_button, upload_button):
        b.config(state="disabled" if busy else "normal")
    stop_button.config(state="normal" if busy else "disabled")


def finish(out):
    root.deiconify()
    root.lift()
    root.bell()
    messagebox.showinfo("Task completed", f"All done!\n\nSaved as:\n{out}", parent=root)
    os.startfile(OUT)


def refresh_voices(select=None):
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(VOICES) if f.endswith(".wav"))
    voice_box.config(values=names)
    if select:
        voice_box.set(select)
    elif names and voice_box.get() not in names:
        voice_box.set(names[0])


def section(title):
    ttk.Separator(root).pack(fill="x", padx=12, pady=(12, 0))
    tk.Label(root, text=title, font=("Segoe UI", 10, "bold")).pack(padx=12, pady=(8, 0), anchor="w")
    frame = tk.Frame(root)
    frame.pack(padx=12, pady=(6, 0), anchor="w", fill="x")
    return frame


root = tk.Tk()
root.title(TITLE)

voice_row = section("1. Voice to use")
tk.Label(voice_row, text="Voice:").pack(side="left")
voice_box = ttk.Combobox(voice_row, state="readonly", width=22)
voice_box.pack(side="left", padx=6)
record_button = tk.Button(voice_row, text="Record my voice", command=toggle_record)
record_button.pack(side="left", padx=6)
upload_button = tk.Button(voice_row, text="Upload a voice...", command=upload_voice)
upload_button.pack(side="left", padx=6)
permission = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="This is my voice, or the person agreed to me using theirs",
               variable=permission).pack(padx=12, pady=(4, 0), anchor="w")

audio_row = section("2. Change the voice of an audio file")
audio_path = tk.StringVar()
tk.Button(audio_row, text="Choose file...", command=choose_audio).pack(side="left")
tk.Label(audio_row, textvariable=audio_path, width=50, anchor="w").pack(side="left", padx=6)
convert_button = tk.Button(audio_row, text="Change voice", command=start_convert, width=14)
convert_button.pack(side="right")

speech_row = section("3. Turn text into speech in that voice")
text_box = tk.Text(root, width=70, height=6, wrap="word")
text_box.pack(padx=12, pady=(0, 4), fill="x")
transcript_title = tk.StringVar()
tk.Button(speech_row, text="Open transcript...", command=open_transcript).pack(side="left")
tk.Label(speech_row, text="Language of the text:").pack(side="left", padx=(12, 0))
language_box = ttk.Combobox(speech_row, values=LANGUAGES, state="readonly", width=12)
language_box.set("English")
language_box.pack(side="left", padx=6)
tk.Label(speech_row, text="Speed:").pack(side="left", padx=(6, 0))
speed_box = ttk.Combobox(speech_row, values=list(SPEEDS), state="readonly", width=14)
speed_box.set("A little slower")
speed_box.pack(side="left", padx=6)
speech_button = tk.Button(speech_row, text="Make speech", command=start_speech, width=14)
speech_button.pack(side="right")
text_box.pack_forget()
text_box.pack(padx=12, pady=(6, 0), fill="x")  # place the text box under its buttons

ttk.Separator(root).pack(fill="x", padx=12, pady=(12, 0))
progress = tk.DoubleVar()
ttk.Progressbar(root, variable=progress, maximum=100).pack(padx=12, pady=(10, 4), fill="x")
status = tk.StringVar(value="Ready.")
tk.Label(root, textvariable=status, wraplength=560, justify="left").pack(padx=12, anchor="w")
stop_button = tk.Button(root, text="Stop", command=stop, width=12, state="disabled")
stop_button.pack(pady=10)

refresh_voices()
root.after(150, bring_to_front)
root.mainloop()
