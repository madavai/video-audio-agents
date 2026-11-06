"""label_speakers end to end with ffmpeg and a stand-in for pyannote's pipeline (CI has neither pyannote nor the
key for its models; the real ones run with -m slow in test_speaker_models.py). The stand-in hears two people
taking turns at fixed times, so which line gets which speaker can be checked exactly."""
import json
import sys
import time
from types import SimpleNamespace

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError

from video_audio_engine import models, progress, speakers

# talk.mp3 is 11 seconds: three lines, and two people taking turns (pyannote's own names; Speaker 1 speaks first).
LINES = [{"start": 0.3, "end": 3.0, "text": "And so my fellow Americans,"},
         {"start": 3.1, "end": 6.4, "text": "ask not what your country can do for you,"},
         {"start": 6.5, "end": 10.8, "text": "ask what you can do for your country."}]
TURNS = [(0.2, 3.3, "SPEAKER_01"), (3.3, 6.0, "SPEAKER_00"), (6.0, 6.6, "SPEAKER_01"), (6.6, 11.0, "SPEAKER_01")]


class StandIn:
    """Answers like pyannote's SpeakerDiarization: calls the hook as it works, returns the turns."""

    def __init__(self):
        self.heard, self.hook_calls, self.delay = None, 0, 0.0

    def __call__(self, audio, num_speakers=None, hook=None):
        self.heard, self.people = audio, num_speakers
        if num_speakers == 3:  # as pyannote does when it finds fewer speakers than asked for
            print("Found only 2 clusters. Using a smaller value than 12 for `min_cluster_size` might help.")
        for step in ("segmentation", "embeddings"):
            for done in range(1, 5):
                time.sleep(self.delay)
                hook(step, None, total=4, completed=done)
                self.hook_calls += 1
        tracks = [(SimpleNamespace(start=start, end=end), "A", who) for start, end, who in TURNS]
        return SimpleNamespace(itertracks=lambda yield_label: iter(tracks))


@pytest.fixture
def stand_in(monkeypatch, with_models):
    pipeline = StandIn()
    monkeypatch.setattr(speakers, "ready", lambda: True)
    monkeypatch.setattr(speakers, "load", lambda job: pipeline)
    return pipeline


@pytest.fixture
def talk(copy_of):
    audio = copy_of("talk.mp3")
    segments = audio.with_name("talk.segments.json")
    segments.write_text(json.dumps(LINES), encoding="utf-8")
    return audio, segments


def test_each_line_gets_its_speaker(stand_in, talk):
    audio, segments = talk
    result = speakers.label_speakers(progress.Job(), str(audio), str(segments))
    assert result == {"transcript_file": str(audio.with_name("talk (speakers).txt")),
                      "segments_file": str(audio.with_name("talk (speakers).segments.json")),
                      "lines": 3, "speakers": {"Speaker 1": 7, "Speaker 2": 3}}
    assert audio.with_name("talk (speakers).txt").read_text(encoding="utf-8") == (
        "[0.3s] Speaker 1: And so my fellow Americans,\n"
        "[3.1s] Speaker 2: ask not what your country can do for you,\n"
        "[6.5s] Speaker 1: ask what you can do for your country.\n")
    labelled = json.loads(audio.with_name("talk (speakers).segments.json").read_text(encoding="utf-8"))
    assert labelled == [line | {"speaker": who} for line, who in zip(LINES, ["Speaker 1", "Speaker 2", "Speaker 1"])]
    assert json.loads(segments.read_text(encoding="utf-8")) == LINES  # the transcript's own files are untouched


def test_the_model_hears_the_recording_at_16_khz(stand_in, talk):
    audio, segments = talk
    speakers.label_speakers(progress.Job(), str(audio), str(segments), people=2)
    waveform = stand_in.heard["waveform"]
    assert stand_in.heard["sample_rate"] == 16000 and stand_in.people == 2
    assert waveform.shape[0] == 1 and 10.5 < waveform.shape[1] / 16000 < 11.5


def test_asking_again_never_overwrites(stand_in, talk):
    audio, segments = talk
    speakers.label_speakers(progress.Job(), str(audio), str(segments))
    result = speakers.label_speakers(progress.Job(), str(audio), str(segments))
    assert result["transcript_file"].endswith("talk (speakers) (2).txt")
    assert result["segments_file"].endswith("talk (speakers) (2).segments.json")


def test_stopping_leaves_no_files(stand_in, talk):
    audio, segments = talk
    stand_in.delay = 0.3  # each step takes a moment, as the real work does

    async def main():
        with anyio.CancelScope() as scope:
            class Ctx:
                async def report_progress(self, percent, total, message):
                    if message == "Telling the voices apart":
                        scope.cancel()
            await progress.run(Ctx(), speakers.label_speakers, str(audio), str(segments), None)

    anyio.run(main)
    assert sorted(p.name for p in audio.parent.iterdir()) == ["talk.mp3", "talk.segments.json"]
    assert stand_in.hook_calls < 8  # it stopped part-way


def test_a_line_where_two_speak_goes_to_who_speaks_most_and_a_gap_to_the_nearest():
    turns = [(0.0, 2.0, "A"), (2.0, 9.0, "B"), (20.0, 25.0, "A")]
    lines = [{"start": 1.0, "end": 4.0, "text": "mostly B"}, {"start": 12.0, "end": 13.0, "text": "nobody: B is nearer"},
             {"start": 17.0, "end": 18.0, "text": "nobody: A is nearer"}]
    assert [line["speaker"] for line in speakers.assign(lines, turns)] == ["Speaker 1", "Speaker 1", "Speaker 2"]


def test_without_the_option_it_says_how_to_set_it_up(talk, private_data):
    audio, segments = talk
    with pytest.raises(ToolError, match='say "set up speaker labels"'):
        speakers.label_speakers(progress.Job(), str(audio), str(segments))
    assert not list(audio.parent.glob("*speakers*"))


def test_wrong_inputs_are_refused_plainly(stand_in, talk):
    audio, segments = talk
    with pytest.raises(ToolError, match="There is no file"):
        speakers.label_speakers(progress.Job(), str(audio.with_name("gone.mp3")), str(segments))
    with pytest.raises(ToolError, match="the .segments.json file transcribe made"):
        speakers.label_speakers(progress.Job(), str(audio), str(audio))
    with pytest.raises(ToolError, match="between 1 and 20"):
        speakers.label_speakers(progress.Job(), str(audio), str(segments), people=0)


def test_the_speaker_model_lets_a_voice_model_go_first(monkeypatch, private_data):
    """One big model in memory at a time, shared with speech-to-text and the voice models."""
    monkeypatch.setattr(models, "loaded", {"multilingual": "a voice model of several GB"})
    monkeypatch.setattr(models, "ensure", lambda names, report: None)
    loaded = []

    class Fake:
        def __getattr__(self, name):
            return lambda *a, **k: loaded.append(name) or self

    fakes = {"pyannote": {}, "pyannote.audio": {"Model": SimpleNamespace(from_pretrained=lambda path: Fake())},
             "pyannote.audio.core": {}, "pyannote.audio.core.task": {"Problem": int, "Resolution": int,
                                                                     "Specifications": dict},
             "pyannote.audio.pipelines": {"SpeakerDiarization": lambda **params: Fake()}}
    for name, parts in fakes.items():  # pyannote isn't installed in the standard setup
        monkeypatch.setitem(sys.modules, name, SimpleNamespace(**parts))
    settings = models.folder("speaker-settings") / "config.yaml"
    settings.parent.mkdir(parents=True)
    settings.write_text("pipeline:\n  params:\n    clustering: AgglomerativeClustering\nparams:\n  clustering: {}\n",
                        encoding="utf-8")
    speakers.load(progress.Job())
    assert list(models.loaded) == ["speakers"] and loaded == ["instantiate"]


def test_what_pyannote_prints_goes_to_the_log_not_to_claude(stand_in, talk, capsys, caplog):
    """stdout carries the engine's messages to Claude: a stray print would break them."""
    audio, segments = talk
    with caplog.at_level("INFO", logger="engine"):
        speakers.label_speakers(progress.Job(), str(audio), str(segments), people=3)
    assert capsys.readouterr().out == ""
    assert "pyannote: Found only 2 clusters" in caplog.text
