"""The person's Hugging Face key: sent only to Hugging Face, only for the gated models (speaker labels, the Kannada
voice), never to the server Hugging Face redirects the download to, and never into a message. No real request is
made: urlopen is replaced."""
import email.message
import urllib.error
import urllib.request

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import models

KEY = "hf_secret_test_key_0123456789"


class Response:
    """What urlopen gives: a file of `size` bytes."""

    def __init__(self, size):
        self.status, self.headers, self.left = 200, {"Content-Length": str(size)}, size

    def read(self, n):
        chunk, self.left = b"x" * min(n, self.left), self.left - min(n, self.left)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def key(private_data):
    private_data.mkdir(parents=True, exist_ok=True)
    (private_data / models.KEY_FILE).write_text(KEY + "\n", encoding="utf-8")
    return private_data / models.KEY_FILE


@pytest.fixture
def requests(monkeypatch):
    """Records each request; answers with a file of the size asked for, or with the HTTP error in answer["code"]."""
    seen, answer = [], {}

    def urlopen(request, timeout):
        seen.append(request)
        if "code" in answer:
            raise urllib.error.HTTPError(request.full_url, answer["code"], "no", email.message.Message(), None)
        return Response(next(size for name in models.SPEAKERS + models.INDIC
                             for file, size in models.MODELS[name]["files"].items()
                             if request.full_url.endswith(f"/{models.MODELS[name]['repo'][1]}/{file}")))

    monkeypatch.setattr(models.urllib.request, "urlopen", urlopen)
    monkeypatch.delenv("VAA_MODELS_URL", raising=False)
    return seen, answer


def test_the_speaker_models_are_pinned_with_exact_sizes():
    for name in models.SPEAKERS:
        repo, revision = models.MODELS[name]["repo"]
        assert repo.startswith("pyannote/") and len(revision) == 40
        assert all(size > 0 for size in models.MODELS[name]["files"].values())
    assert {repo for repo, feature in models.GATED.items() if feature == "speaker labels"} < {
        models.MODELS[name]["repo"][0] for name in models.SPEAKERS}
    assert not set(models.SPEAKERS) & set(models.FULL)  # an option, not part of the full setup


def test_the_kannada_voice_is_pinned_gated_and_an_option():
    repo, revision = models.MODELS["kannada"]["repo"]
    assert repo == "ai4bharat/IndicF5" and len(revision) == 40 and models.GATED[repo] == "the Kannada voice"
    assert models.MODELS["kannada"]["files"] == {"model.safetensors": 1402789408, "checkpoints/vocab.txt": 11283}
    assert "kannada" not in models.FULL and models.INDIC == ["kannada", "large-v3-turbo"]  # it checks each reading
    assert models.MODELS["large-v3-turbo"]["repo"][0] not in models.GATED


def test_a_gated_file_gets_the_key_only_for_hugging_face_itself(key, requests):
    models.ensure(["speaker-settings"])
    request = requests[0][-1]
    assert request.full_url.startswith("https://huggingface.co/pyannote/speaker-diarization-3.1/resolve/84fd259")
    assert request.unredirected_hdrs["Authorization"] == f"Bearer {KEY}"
    assert "Authorization" not in request.headers  # the headers a redirect passes on
    assert models.is_present("speaker-settings")


def test_a_redirect_does_not_pass_the_key_on(key, requests):
    """Hugging Face sends model files from another server: urllib copies only the redirectable headers."""
    models.ensure(["speaker-turns"])
    moved = urllib.request.HTTPRedirectHandler().redirect_request(
        requests[0][-1], None, 302, "Found", {}, "https://cdn.example.org/file")
    assert "Authorization" not in moved.headers and "Authorization" not in moved.unredirected_hdrs


def test_an_open_model_is_downloaded_without_the_key(key, requests):
    models.ensure(["speaker-voices"])
    assert not requests[0][-1].has_header("Authorization")


def test_without_a_key_the_person_is_told_to_set_it_up(private_data, requests):
    with pytest.raises(ToolError, match='say "set up speaker labels"'):
        models.ensure(["speaker-settings"])
    with pytest.raises(ToolError, match='say "set up the Kannada voice"'):
        models.ensure(["kannada"])
    assert requests[0] == []  # nothing was asked of Hugging Face


def test_the_kannada_voice_downloads_with_the_key_into_its_own_folder(key, requests, monkeypatch):
    small = dict(models.MODELS["kannada"], files={"model.safetensors": 1000, "checkpoints/vocab.txt": 10})
    monkeypatch.setitem(models.MODELS, "kannada", small)  # its real size, without writing 1.4 GB
    models.ensure(["kannada"])
    urls = [request.full_url for request in requests[0]]
    assert urls == [f"https://huggingface.co/ai4bharat/IndicF5/resolve/{models.MODELS['kannada']['repo'][1]}/{file}"
                    for file in ("model.safetensors", "checkpoints/vocab.txt")]
    assert all(request.unredirected_hdrs["Authorization"] == f"Bearer {KEY}" for request in requests[0])
    assert (models.models_dir() / "IndicF5" / "checkpoints" / "vocab.txt").is_file()


def test_a_key_hugging_face_doesnt_know_is_forgotten(key, requests):
    requests[1]["code"] = 401
    with pytest.raises(ToolError, match="didn't accept the saved key") as refused:
        models.ensure(["speaker-settings"])
    assert not key.exists()  # so the setup asks for it again
    assert KEY not in str(refused.value)


def test_terms_not_accepted_names_both_pages_and_keeps_the_key(key, requests):
    requests[1]["code"] = 403
    with pytest.raises(ToolError) as refused:
        models.ensure(["speaker-turns"])
    message = str(refused.value)
    assert "https://huggingface.co/pyannote/segmentation-3.0" in message
    assert "https://huggingface.co/pyannote/speaker-diarization-3.1" in message
    assert "IndicF5" not in message and 'say "set up speaker labels" again' in message
    assert key.exists() and KEY not in message


def test_kannada_terms_not_accepted_name_only_its_page(key, requests):
    requests[1]["code"] = 403
    with pytest.raises(ToolError) as refused:
        models.ensure(["kannada"])
    message = str(refused.value)
    assert "https://huggingface.co/ai4bharat/IndicF5" in message and "pyannote" not in message
    assert 'say "set up the Kannada voice" again' in message and key.exists()


def test_the_setup_says_one_line_for_the_three_speaker_files(monkeypatch, capsys):
    """The speaker models are three small files under one name: one "downloading" line, not "already here" after it."""
    from video_audio_engine import server
    monkeypatch.setattr(models, "ffmpeg_present", lambda: True)
    monkeypatch.setattr(models, "ensure_ffmpeg", lambda report: None)
    monkeypatch.setattr(models, "is_present", lambda name: name == "speaker-voices")  # fetched once before
    fetched = []
    monkeypatch.setattr(models, "ensure", lambda names, report: fetched.append(names))
    server.warm("speakers")
    lines = capsys.readouterr().out.splitlines()
    assert lines[1:3] == ["speaker labels: downloading (under 0.1 GB)", f"Done. Models are in {models.models_dir()}"]
    assert fetched == [models.SPEAKERS]
