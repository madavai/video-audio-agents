import functools
import http.server
import os
import re
import shutil
import subprocess
import threading
import time
import types
from pathlib import Path

import pytest

from video_audio_engine import models, paths

FIXTURES = Path(__file__).parent / "fixtures"
SHARED = Path(__file__).parent.parent / ".test-data"  # ffmpeg and the fast speech model, kept between runs


@pytest.fixture(autouse=True)
def private_data(tmp_path, monkeypatch):
    """Every test gets its own empty data folder and Documents folder: nothing touches the person's real files."""
    monkeypatch.setenv("VAA_DATA", str(tmp_path / "data"))
    monkeypatch.setattr(paths, "documents_dir", lambda: tmp_path / "Documents")
    return tmp_path / "data"


@pytest.fixture
def listener(monkeypatch):
    """The accurate speech-to-text model, stood in for where it checks that a Kannada reading says the sentence
    (voices.says_sentence): it hears `listener.words` (the sentence, unless a test changes them) and counts in
    `listener.times` how often it listened."""
    from video_audio_engine import transcribe, voices
    listener = types.SimpleNamespace(words=voices.SENTENCE, times=0)

    class Pipeline:
        def transcribe(self, audio, language):
            assert language == "kn"
            listener.times += 1
            return [types.SimpleNamespace(text=listener.words)], None

    def load(name, report, device=None):
        assert name == "large-v3-turbo" and device == "cpu"
        return Pipeline(), device

    monkeypatch.setattr(transcribe, "load", load)
    monkeypatch.setattr(voices, "heard", {})
    return listener


@pytest.fixture(scope="session")
def ffmpeg():
    """ffmpeg, downloaded once into the shared test data folder."""
    old = os.environ.get("VAA_DATA")
    os.environ["VAA_DATA"] = str(SHARED)
    try:
        folder = models.ensure_ffmpeg()
    finally:
        if old is None:
            del os.environ["VAA_DATA"]
        else:
            os.environ["VAA_DATA"] = old
    return str(folder / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))


@pytest.fixture
def meter(ffmpeg):
    """A function that gives a file's integrated loudness in LUFS, measured by ffmpeg's EBU R128 meter."""
    def measure(file):
        said = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(file), "-af", "ebur128", "-f", "null", "-"],
                              capture_output=True, text=True).stderr
        return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", said)[-1])
    return measure


@pytest.fixture
def with_models(monkeypatch, ffmpeg):
    """Use the shared data folder (ffmpeg, and the fast speech model once a test has downloaded it)."""
    monkeypatch.setenv("VAA_DATA", str(SHARED))
    return SHARED


@pytest.fixture(scope="session")
def media(ffmpeg, tmp_path_factory):
    """Test media made by ffmpeg from the 11-second speech sample: never downloaded, never committed."""
    folder = tmp_path_factory.mktemp("web")
    speech = str(FIXTURES / "jfk.wav")

    def make(*args):
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", *args], check=True, cwd=folder)

    make("-i", speech, "talk.mp3")
    make("-f", "lavfi", "-i", "testsrc=size=320x240:rate=25", "-i", speech, "-shortest",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "talk.mp4")
    make("-i", "talk.mp4", "-c:v", "libtheora", "-c:a", "libvorbis", "talk.ogv")  # can't go into an mp4 as is
    (folder / "hls").mkdir()
    make("-i", "talk.mp4", "-c", "copy", "-f", "hls", "-hls_time", "2", "-hls_playlist_type", "vod",
         "hls/index.m3u8")
    make("-stream_loop", "9", "-i", speech, "long.mp3")  # 110 seconds
    make("-f", "lavfi", "-i", "testsrc=size=320x240:rate=25", "-i", "long.mp3", "-shortest",
         "-c:v", "libx264", "-g", "50", "-pix_fmt", "yuv420p", "-c:a", "aac", "long.mp4")  # a keyframe every 2 s
    make("-f", "lavfi", "-i", "sine=frequency=440:duration=180", "-b:a", "128k", "slow.mp3")
    # A wide 16:9 picture in three bands, red | green | blue, so an upright crop shows which part it kept.
    make("-f", "lavfi", "-i", "color=red:size=427x720:rate=25", "-f", "lavfi", "-i", "color=green:size=426x720:rate=25",
         "-f", "lavfi", "-i", "color=blue:size=427x720:rate=25", "-i", speech, "-filter_complex", "[0][1][2]hstack=3[v]",
         "-map", "[v]", "-map", "3:a", "-t", "8", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "thirds.mp4")
    # A video narrated over music (a tone and soft noise throughout, the speech from 0:03), and a beep as its dub.
    make("-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=20", "-f", "lavfi",
         "-i", "sine=frequency=220:duration=20,volume=0.1", "-f", "lavfi",
         "-i", "anoisesrc=color=pink:duration=20:amplitude=0.03:seed=1", "-i", speech, "-filter_complex",
         "[3]adelay=3000|3000[s];[1][2][s]amix=inputs=3:normalize=0[a]", "-map", "0:v", "-map", "[a]",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "narrated.mp4")
    make("-f", "lavfi", "-i", "sine=frequency=880:duration=11,volume=0.05", "-af", "adelay=3000", "beep.mp3")
    # A quiet recording (about -27 LUFS) with 3 s of near-silence before the speech and 4 s after it.
    make("-f", "lavfi", "-i", "anoisesrc=color=pink:duration=3:amplitude=0.001:seed=2", "-i", speech, "-f", "lavfi",
         "-i", "anoisesrc=color=pink:duration=4:amplitude=0.001:seed=3", "-filter_complex",
         "[0]aresample=16000[a];[1]volume=-12dB[s];[2]aresample=16000[b];[a][s][b]concat=n=3:v=0:a=1", "quiet.mp3")
    # A narration and its music as tones, so each can be found again in a mix: a voice (400 Hz, 2 s on and 3 s off, three
    # times: 15 s), a short piece of music (500 Hz, repeated to fill the 15 s; the loud one 20 dB hotter), an intro
    # (600 Hz) and an outro (800 Hz), 2 s each.
    make("-f", "lavfi", "-i", "aevalsrc='0.1*sin(2*PI*400*t)*lt(mod(t,5),2)':d=15:s=44100", "bursts.wav")
    make("-f", "lavfi", "-i", "sine=frequency=500:duration=6,volume=0.2", "bed.mp3")
    make("-f", "lavfi", "-i", "sine=frequency=500:duration=6,volume=2", "bed_loud.mp3")
    make("-f", "lavfi", "-i", "sine=frequency=600:duration=2,volume=2", "intro.mp3")
    make("-f", "lavfi", "-i", "sine=frequency=800:duration=2,volume=2", "outro.mp3")
    # A lesson page whose video is added by a script, so only a real browser finds it.
    (folder / "lesson.html").write_text(
        "<html><head><title>Lesson one</title></head><body><video id=v controls></video><script>"
        "setTimeout(() => { document.getElementById('v').src = '/talk' + '.mp' + '4'; }, 300);"
        "</script></body></html>", encoding="utf-8")
    (folder / "empty.html").write_text("<html><head><title>Nothing here</title></head><body>Hello</body></html>",
                                       encoding="utf-8")
    return folder


class Files(http.server.SimpleHTTPRequestHandler):
    """Serves the test media. Files named slow.* trickle out, so a download can be stopped part-way."""

    def copyfile(self, source, outputfile):
        if "slow" not in self.path:
            return super().copyfile(source, outputfile)
        while chunk := source.read(16384):
            outputfile.write(chunk)
            time.sleep(0.05)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def web(media):
    """A local web server for the test media; returns its address."""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Files, directory=str(media)))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.fixture
def copy_of(tmp_path, media):
    """A fresh copy of a test media file in this test's own folder."""
    def copy(name):
        target = tmp_path / "work" / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy(media / name, target)
        return target
    return copy
