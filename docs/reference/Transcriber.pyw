import glob, os, re, subprocess, sys, threading, tkinter as tk
from tkinter import ttk, messagebox

OUT = r"C:\Audio"
PROFILE = os.path.join(OUT, "browser-profile")  # keeps you logged in between runs
os.makedirs(OUT, exist_ok=True)
TITLE = "Video Transcriber"
# The Python that has the Transcriber's helpers installed.
PYTHON = r"C:\Users\chait\AppData\Local\Programs\Python\Python311\pythonw.exe"
NEEDS = ["yt_dlp", "faster_whisper", "playwright"]
FIX = ('In PowerShell, run:\n& "C:\\Users\\chait\\AppData\\Local\\Programs\\Python\\Python311\\python.exe" '
       '-m pip install -U yt-dlp faster-whisper playwright deep-translator')


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


start_up(PYTHON, NEEDS, FIX, "log.txt", TITLE)

ACCURACY = {"Fast (rougher)": "base", "Balanced": "small", "Accurate (slower)": "medium"}
NO_TRANSLATION = "No translation"
LANGUAGES = {"English": "en", "Kannada": "kn", "Hindi": "hi", "French": "fr", "Spanish": "es", "Tamil": "ta"}
ENGINES = ["Google (online)", "Argos (offline)"]
stop_flag = threading.Event()


class Stopped(BaseException):
    """Raised when Stop is pressed. A BaseException, so per-link error handling doesn't catch it."""


def check_stop():
    if stop_flag.is_set():
        raise Stopped()


def find_streams(links):
    """Returns (link, stream, title) per link. Links the downloader understands by itself
    (YouTube, Vimeo, direct .mp4/.mp3 files and many more) are used directly; other pages,
    such as ones behind a login, are opened in Edge to catch their video or audio."""
    import yt_dlp
    results = {}
    for i, link in enumerate(links, 1):
        check_stop()
        say(f"Checking link {i} of {len(links)}...")
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
                results[link] = (link, ydl.extract_info(link, download=False)["title"])
        except Exception:
            pass  # not directly downloadable; try it in the browser below
    pages = [link for link in links if link not in results]
    if pages:
        results.update(open_pages(pages))
    return [(link, *results[link]) for link in links]


def open_pages(links):
    """Open each lesson in Edge and catch its video stream link."""
    from playwright.sync_api import sync_playwright
    results, found = {}, []
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(PROFILE, channel="msedge", headless=False)
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.on("request", lambda r: not found and (r.resource_type == "media" or ".m3u8" in r.url
                                                    or ".mpd" in r.url) and found.append(r.url))
        for i, link in enumerate(links, 1):
            found.clear()
            say(f"Finding video {i} of {len(links)}. If asked, log in and open the lesson in the browser "
                "window. Press play if the video doesn't start by itself.")
            page.goto(link)
            for _ in range(300 if i == 1 else 30):  # 10 minutes for the first (time to log in), 1 minute after
                check_stop()
                if found:
                    break
                for frame in page.frames:
                    try:
                        frame.evaluate("document.querySelectorAll('video').forEach(v => { v.muted = true; v.play(); })")
                    except Exception:
                        pass
                page.wait_for_timeout(2000)
            results[link] = (found[0] if found else None, page.title())
        browser.close()
    return results


def download(url, base, video, mp3, label):
    """Download only what's needed: the .mp4, the .mp3, or both."""
    import yt_dlp
    opts = {"outtmpl": base + ".%(ext)s", "quiet": True, "noprogress": True, "noplaylist": True}
    if video:
        opts.update({"format": "bestvideo+bestaudio/best", "merge_output_format": "mp4", "keepvideo": True})
    else:
        opts["format"] = "bestaudio/best"
    if mp3:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    def report(d):
        check_stop()
        if d["status"] != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        if d.get("fragment_count"):  # streams arrive in numbered pieces
            pct = d.get("fragment_index", 0) / d["fragment_count"] * 100
        elif total:
            pct = d["downloaded_bytes"] / total * 100
        else:
            return
        say(f"{label}... {int(pct)}%", pct)
    opts["progress_hooks"] = [report]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def transcribe(model, mp3, tag):
    """Returns the start times, the text lines, and the detected spoken language."""
    segments, info = model.transcribe(mp3)
    starts, texts = [], []
    for s in segments:
        check_stop()
        if s.text.strip():
            starts.append(s.start)
            texts.append(s.text.strip())
        pct = s.end / info.duration * 100
        say(f"{tag}: transcribing... {int(pct)}%", pct)
    return starts, texts, info.language


def translate(texts, src, dst, engine):
    if engine.startswith("Google"):
        from deep_translator import GoogleTranslator
        google = GoogleTranslator(source="auto", target=dst)
        out, i = [], 0
        while i < len(texts):  # send lines in batches to stay under Google's size limit
            check_stop()
            chunk = []
            while i < len(texts) and (not chunk or sum(len(t) + 1 for t in chunk) + len(texts[i]) < 4500):
                chunk.append(texts[i])
                i += 1
            result = google.translate("\n".join(chunk)).split("\n")
            out += result if len(result) == len(chunk) else [google.translate(t) for t in chunk]
        return out

    import argostranslate.package as pkg, argostranslate.translate as argos
    src, dst = src.split("-")[0], dst.split("-")[0]
    pairs = [(src, dst)] if "en" in (src, dst) else [(src, "en"), ("en", dst)]  # offline packs go via English
    installed = {(p.from_code, p.to_code) for p in pkg.get_installed_packages()}
    if any(pair not in installed for pair in pairs):
        say("Downloading the offline language pack (one time only)...")
        pkg.update_package_index()
        available = {(p.from_code, p.to_code): p for p in pkg.get_available_packages()}
        for pair in pairs:
            if pair not in installed:
                if pair not in available:
                    raise RuntimeError(f"Offline translation {pair[0]} to {pair[1]} isn't available. Try Google (online).")
                pkg.install_from_path(available[pair].download())
    return [argos.translate(t, src, dst) for t in texts]


def unique_base(name):
    """A file name not used yet in the folder, so each link gets its own files (adds (2), (3)... if needed)."""
    base, n = os.path.join(OUT, name), 2
    while glob.glob(glob.escape(base) + ".*"):
        base, n = os.path.join(OUT, f"{name} ({n})"), n + 1
    return base


def save(path, starts, texts, timestamps):
    with open(path, "w", encoding="utf-8") as f:
        if timestamps:
            for start, text in zip(starts, texts):
                f.write(f"[{start:.1f}s] {text}\n")
            return
        paragraphs, current = [], ""
        for text in texts:  # flowing text, new paragraph after a sentence once it gets long
            current = f"{current} {text}".strip()
            if len(current) > 400 and text.endswith((".", "?", "!", "\u3002")):
                paragraphs.append(current)
                current = ""
        f.write("\n\n".join(paragraphs + [current] if current else paragraphs) + "\n")


def run(links, video, audio, transcript, accuracy, timestamps, language, engine):
    failed, base = [], None
    try:
        streams = find_streams(links)
        model = None
        for i, (link, url, title) in enumerate(streams, 1):
            tag = f"Link {i} of {len(streams)}"
            if not url:
                failed.append(f"{link}\n   Couldn't find the video on this page.")
                continue
            try:
                name = re.sub(r'[\\/:*?"<>|]', "", title).strip()[:80] or f"lesson {i}"
                base = unique_base(name)
                what = "video and audio" if video and (audio or transcript) else "video" if video else "audio"
                download(url, base, video, audio or transcript, f"{tag}: downloading {what}")  # transcript is made from audio
                if transcript:
                    if model is None:
                        say(f"{tag}: preparing transcription (first use downloads the model)...")
                        from faster_whisper import WhisperModel
                        model = WhisperModel(ACCURACY[accuracy], device="cpu", compute_type="int8")
                    starts, texts, spoken = transcribe(model, base + ".mp3", tag)
                    save(base + ".txt", starts, texts, timestamps)
                    if language != NO_TRANSLATION and LANGUAGES[language].split("-")[0] != spoken:
                        say(f"{tag}: translating to {language}...", 0)
                        save(f"{base} ({language}).txt", starts, translate(texts, spoken, LANGUAGES[language], engine), timestamps)
                    if not audio:
                        os.remove(base + ".mp3")  # only needed to make the transcript
            except Exception as e:
                failed.append(f"{link}\n   {e}")
        done = len(streams) - len(failed)
        say(f"Done: {done} of {len(streams)} finished. Files are in {OUT}.", 100)
        root.after(0, finish, done, len(streams), failed)
    except Stopped:
        if base:  # remove half-downloaded pieces of the item that was in progress
            for leftover in glob.glob(glob.escape(base) + ".*"):
                if ".part" in leftover or leftover.endswith((".ytdl", ".temp")):
                    os.remove(leftover)
        say(f"Stopped. Anything already finished is kept in {OUT}.", 0)
    except Exception as e:
        say("Something went wrong.")
        root.after(0, lambda: messagebox.showerror("Error", str(e)))
    finally:
        root.after(0, lambda: (button.config(state="normal"), stop_button.config(state="disabled")))


def start():
    links = [line.strip() for line in links_box.get("1.0", "end").splitlines() if line.strip()]
    if not links:
        status.set("Paste at least one link.")
    elif not (want_video.get() or want_audio.get() or want_text.get()):
        status.set("Tick at least one box: Video, Audio or Transcript.")
    elif language_box.get() != NO_TRANSLATION and not want_text.get():
        status.set("Translation needs the Transcript box ticked.")
    else:
        stop_flag.clear()
        button.config(state="disabled")
        stop_button.config(state="normal")
        progress.set(0)
        args = (links, want_video.get(), want_audio.get(), want_text.get(),
                accuracy_box.get(), want_times.get(), language_box.get(), engine_box.get())
        threading.Thread(target=run, args=args, daemon=True).start()


def stop():
    stop_flag.set()
    stop_button.config(state="disabled")
    status.set("Stopping... (finishing the current small step)")


def say(msg, pct=None):
    root.after(0, status.set, msg)
    if pct is not None:
        root.after(0, progress.set, pct)


def finish(done, total, failed):
    """Bring the app to the front and pop up a completion message."""
    root.deiconify()
    root.lift()
    root.bell()
    if failed:
        messagebox.showwarning("Finished with problems", f"{done} of {total} finished. These links failed:\n\n"
                               + "\n\n".join(failed), parent=root)
    else:
        messagebox.showinfo("Task completed", f"All done! {done} of {total} finished.\n\nYour files are in {OUT}.",
                            parent=root)
    os.startfile(OUT)


def row(label):
    frame = tk.Frame(root)
    frame.pack(padx=12, pady=(10, 0), anchor="w")
    tk.Label(frame, text=label).pack(side="left")
    return frame


root = tk.Tk()
root.title(TITLE)
tk.Label(root, text="Paste video or audio links, one per line:").pack(padx=12, pady=(12, 4), anchor="w")
links_box = tk.Text(root, width=70, height=6)
links_box.pack(padx=12)

boxes = row("Save:")
want_video, want_audio, want_text = tk.BooleanVar(value=True), tk.BooleanVar(value=True), tk.BooleanVar(value=True)
tk.Checkbutton(boxes, text="Video (.mp4)", variable=want_video).pack(side="left", padx=6)
tk.Checkbutton(boxes, text="Audio (.mp3)", variable=want_audio).pack(side="left", padx=6)
tk.Checkbutton(boxes, text="Transcript (.txt)", variable=want_text).pack(side="left", padx=6)

accuracy_row = row("Transcript accuracy:")
accuracy_box = ttk.Combobox(accuracy_row, values=list(ACCURACY), state="readonly", width=18)
accuracy_box.set("Balanced")
accuracy_box.pack(side="left", padx=6)
want_times = tk.BooleanVar(value=True)
tk.Checkbutton(accuracy_row, text="Include timestamps", variable=want_times).pack(side="left", padx=6)

translate_row = row("Translate transcript to:")
language_box = ttk.Combobox(translate_row, values=[NO_TRANSLATION] + list(LANGUAGES), state="readonly", width=16)
language_box.set(NO_TRANSLATION)
language_box.pack(side="left", padx=6)
tk.Label(translate_row, text="using").pack(side="left")
engine_box = ttk.Combobox(translate_row, values=ENGINES, state="readonly", width=16)
engine_box.set(ENGINES[0])
engine_box.pack(side="left", padx=6)

buttons = tk.Frame(root)
buttons.pack(pady=12)
button = tk.Button(buttons, text="Start", command=start, width=12)
button.pack(side="left", padx=6)
stop_button = tk.Button(buttons, text="Stop", command=stop, width=12, state="disabled")
stop_button.pack(side="left", padx=6)
progress = tk.DoubleVar()
ttk.Progressbar(root, variable=progress, maximum=100, length=520).pack(padx=12, pady=(0, 6), anchor="w")
status = tk.StringVar(value="Ready.")
tk.Label(root, textvariable=status, wraplength=520, justify="left").pack(padx=12, pady=(0, 12), anchor="w")
root.after(150, bring_to_front)
root.mainloop()
