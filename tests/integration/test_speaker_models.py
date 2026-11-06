"""The real speaker models and the real graphics card (run with -m slow, on a computer that has them). Speaker
labels need the engine's environment synced with `--extra speakers` and the three speaker models in
.test-data/models/ (copied from a data folder where "set up speaker labels" ran: two are gated, so tests can't
download them). The card needs `--extra gpu` and an NVIDIA card; each test is skipped when its part is missing."""
import json
import re
import subprocess

import pytest

from video_audio_engine import gpu, models, progress, speakers, transcribe

pytestmark = pytest.mark.slow


@pytest.fixture
def two_voices(tmp_path, ffmpeg, media):
    """The 11-second speech twice, the second time a fifth lower (a different-sounding voice), 1 s apart."""
    audio = tmp_path / "two.mp3"
    subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(media / "talk.mp3"), "-filter_complex",
                    "[0]aresample=44100,asplit[a][b];[b]asetrate=44100*0.67,aresample=44100,atempo=1.4925[low];"
                    "anullsrc=r=44100:cl=mono:d=1[gap];[a]aformat=channel_layouts=mono[a1];"
                    "[low]aformat=channel_layouts=mono[b1];[a1][gap][b1]concat=n=3:v=0:a=1", str(audio)], check=True)
    return audio


def test_two_voices_get_two_labels(two_voices, with_models):
    pytest.importorskip("pyannote.audio")
    if not all(models.is_present(name) for name in models.SPEAKERS):
        pytest.skip("the speaker models aren't in .test-data/models/")
    transcribed = transcribe.transcribe(progress.Job(), str(two_voices), "fast")
    result = speakers.label_speakers(progress.Job(), str(two_voices), transcribed["segments_file"], people=2)
    lines = json.loads(open(result["segments_file"], encoding="utf-8").read())
    first = {line["speaker"] for line in lines if line["end"] < 11.5}
    second = {line["speaker"] for line in lines if line["start"] > 12}
    assert first == {"Speaker 1"} and second == {"Speaker 2"}
    assert list(models.loaded) == ["speakers"]  # one big model in memory


def test_a_transcript_on_the_card_has_the_same_words(copy_of, with_models, monkeypatch):
    if not gpu.usable():
        pytest.skip("no NVIDIA card with the graphics-card option here")
    monkeypatch.setattr(models, "loaded", {})
    on_card = transcribe.transcribe(progress.Job(), str(copy_of("talk.mp3")), "fast")
    assert list(models.loaded) == [("base", "cuda")] and "note" not in on_card
    monkeypatch.setattr(gpu, "failed", "comparing with the processor")
    on_processor = transcribe.transcribe(progress.Job(), str(copy_of("talk.mp4")), "fast")
    words = [re.sub(r"\[[\d.]+s\] ", "", open(r["transcript_file"], encoding="utf-8").read()).lower().split()
             for r in (on_card, on_processor)]
    assert words[0] == words[1] and "country" in words[0]
