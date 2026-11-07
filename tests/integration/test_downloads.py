"""models.py against a local web server that, like Hugging Face, can resume a download part-way."""
import http.server
import threading

import pytest

from video_audio_engine import models

CONTENT = bytes(range(256)) * 4096  # 1 MB of test "model"


class Server(http.server.BaseHTTPRequestHandler):
    drop_after = None  # bytes to send before cutting the connection once (a broken download)
    ranges = []
    keys = []  # Authorization headers received: must stay empty, this isn't Hugging Face

    def do_GET(self):
        Server.keys += [self.headers["Authorization"]] if self.headers.get("Authorization") else []
        start = 0
        if self.headers.get("Range"):
            Server.ranges.append(self.headers["Range"])
            start = int(self.headers["Range"].split("=")[1].split("-")[0])
        body = CONTENT[start:]
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if Server.drop_after:
            body, Server.drop_after = body[:Server.drop_after], None
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def server(monkeypatch):
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Server)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    Server.ranges, Server.drop_after, Server.keys = [], None, []
    monkeypatch.setenv("VAA_MODELS_URL", f"http://127.0.0.1:{httpd.server_port}")
    monkeypatch.setitem(models.MODELS, "test-model", {
        "label": "test model", "repo": ("test/test-model", "0" * 40), "files": {"model.bin": len(CONTENT)}})
    yield httpd
    httpd.shutdown()


def test_a_missing_model_is_downloaded_with_progress(server):
    seen = []
    assert models.missing_gb(["test-model"]) == 0.0 and not models.is_present("test-model")
    models.ensure(["test-model"], lambda pct, msg: seen.append((pct, msg)))
    assert models.is_present("test-model")
    assert (models.folder("test-model") / "model.bin").read_bytes() == CONTENT
    assert seen[-1][0] == 100 and "test model" in seen[-1][1]
    assert not list(models.folder("test-model").glob("*.part"))


def test_a_broken_download_continues_where_it_stopped(server):
    Server.drop_after = 300_000
    with pytest.raises(OSError):
        models.ensure(["test-model"])
    part = models.folder("test-model") / "model.bin.part"
    assert part.stat().st_size == 300_000 and not models.is_present("test-model")

    models.ensure(["test-model"])
    assert Server.ranges == ["bytes=300000-"]
    assert (models.folder("test-model") / "model.bin").read_bytes() == CONTENT
    assert not part.exists()


def test_nothing_is_downloaded_when_the_model_is_there(server):
    models.ensure(["test-model"])
    Server.ranges.clear()
    models.ensure(["test-model"], lambda pct, msg: pytest.fail("should not download again"))


def test_a_gated_model_from_elsewhere_never_gets_the_key(server, private_data, monkeypatch):
    """The key goes only to Hugging Face: a model downloaded from another address (here the test server, as
    VAA_MODELS_URL does) is fetched without it, even for a gated model."""
    private_data.mkdir(parents=True, exist_ok=True)
    (private_data / models.KEY_FILE).write_text("hf_secret_test_key", encoding="utf-8")
    gated = dict(models.MODELS["test-model"], repo=(models.GATED[0], "0" * 40))
    monkeypatch.setitem(models.MODELS, "test-model", gated)
    models.ensure(["test-model"])
    assert models.is_present("test-model") and Server.keys == []
