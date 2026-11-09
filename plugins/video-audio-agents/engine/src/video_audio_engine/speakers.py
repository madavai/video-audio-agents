"""label_speakers: who said what. pyannote's speaker diarization 3.1 finds who speaks when, and each line of a
transcript gets the speaker who talks most during it. Installed only by the setup's speaker labels option; its
models are unlocked by the person's Hugging Face key (models.SPEAKERS). Runs on the processor (see gpu.py)."""
import contextlib
import gc
import importlib.util
import io
import json
import logging
from pathlib import Path

from mcp.server.mcpserver.exceptions import ToolError

from . import models, paths, voices
from .paths import data_dir

log = logging.getLogger("engine")
RATE = 16000  # the models listen at 16 kHz
# The pipeline hears 10-second windows; pyannote's default moves them on by 1 s, so every moment is heard 10 times and
# the voice model takes 95% of the time. Every 5 s (half a window) was 5.5 times faster on the processor (48 s against
# 264 s for 10 minutes of a NASA podcast) and labelled the two real podcasts just as right (see CHANGELOG 1.4.0).
STEP = 0.5
STEPS = {"segmentation": (5, 35, "Finding who speaks when"), "embeddings": (35, 95, "Telling the voices apart")}


@contextlib.contextmanager
def printed_to_log(library: str = "pyannote"):
    """pyannote prints notes (a model made with an older version, fewer speakers found than asked for), so does
    F5-TTS (indic.py), and stdout carries the MCP messages: they go to the log file instead."""
    said = io.StringIO()
    try:
        with contextlib.redirect_stdout(said):
            yield
    finally:
        if said.getvalue().strip():
            log.info("%s: %s", library, said.getvalue().strip())


def ready() -> bool:
    """Whether speaker labels can run: pyannote installed, and its models here or the key to download them."""
    try:
        installed = importlib.util.find_spec("pyannote.audio") is not None
    except ModuleNotFoundError:  # no pyannote package at all
        installed = False
    downloaded = all(models.is_present(name) for name in models.SPEAKERS)
    return installed and (downloaded or (data_dir() / models.KEY_FILE).exists())


def load(job):
    """pyannote's pipeline, built from the downloaded files: its settings, with the two models loaded from their
    folders in place of their Hugging Face names, so it never downloads anything itself."""
    if "speakers" not in models.loaded:
        models.ensure(models.SPEAKERS, job.report)
        job.report(0, "Loading the speaker model")
        import torch
        import yaml
        from pyannote.audio import Model
        from pyannote.audio.core.task import Problem, Resolution, Specifications
        from pyannote.audio.pipelines import SpeakerDiarization
        models.loaded.clear()  # a voice model takes several GB: let it go first
        gc.collect()
        settings = yaml.safe_load((models.folder("speaker-settings") / "config.yaml").read_text(encoding="utf-8"))
        # PyTorch 2.6 opens model files "weights only" (a file can't run code) and refuses the four plain types
        # these files also hold until they are named here; the check itself stays on.
        with printed_to_log(), torch.serialization.safe_globals([torch.torch_version.TorchVersion, Specifications,
                                                                  Problem, Resolution]):
            # Models, not paths: pyannote picks how to load a voice model by words in its path ("wespeaker": ONNX).
            pipeline = SpeakerDiarization(**settings["pipeline"]["params"] | {
                "segmentation": Model.from_pretrained(models.folder("speaker-turns") / "pytorch_model.bin"),
                "embedding": Model.from_pretrained(models.folder("speaker-voices") / "pytorch_model.bin"),
                "segmentation_step": STEP})
        models.loaded["speakers"] = pipeline.instantiate(settings["params"])
    return models.loaded["speakers"]


def who_speaks_when(pipeline, audio, people, job) -> list:
    """[(start, end, speaker)] for every stretch of speech, from 16 kHz mono samples."""
    import torch

    def hook(step, artifact, file=None, total=None, completed=None):
        low, high, message = STEPS.get(step, (95, 95, "Telling the voices apart"))
        job.report(low + (high - low) * (completed or 0) / (total or 1), message)  # also stops the work after Esc

    with printed_to_log():
        found = pipeline({"waveform": torch.from_numpy(audio).unsqueeze(0), "sample_rate": RATE},
                         num_speakers=people, hook=hook)
    return [(turn.start, turn.end, who) for turn, _, who in found.itertracks(yield_label=True)]


def assign(lines: list, turns: list) -> list:
    """Each line with the speaker who talks most during it (the nearest one if nobody does), named Speaker 1,
    Speaker 2... in the order they first speak."""
    names, labelled = {}, []
    for line in lines:
        talk = {}
        for start, end, who in turns:
            overlap = min(end, line["end"]) - max(start, line["start"])
            if overlap > 0:
                talk[who] = talk.get(who, 0) + overlap
        who = max(talk, key=talk.get) if talk else \
            min(turns, key=lambda turn: max(turn[0] - line["end"], line["start"] - turn[1]))[2]
        labelled.append(line | {"speaker": names.setdefault(who, f"Speaker {len(names) + 1}")})
    return labelled


def label_speakers(job, file: str, segments_file: str, people: int | None = None) -> dict:
    source, segments = Path(file), Path(segments_file)
    for path in (source, segments):
        if not path.is_file():
            raise ToolError(f"There is no file at {path}.")
    if not segments.name.endswith(".segments.json"):
        raise ToolError("segments_file must be the .segments.json file transcribe made.")
    if people is not None and not 1 <= people <= 20:
        raise ToolError("people must be between 1 and 20 (or left out when it isn't known).")
    if not ready():
        raise ToolError('Speaker labels aren\'t set up on this computer yet: say "set up speaker labels" (it needs '
                        "a free Hugging Face account).")
    lines = json.loads(segments.read_text(encoding="utf-8"))
    if not lines:
        raise ToolError(f"{segments.name} has no lines to label.")
    with models.one_at_a_time(job):
        pipeline = load(job)
        job.report(2, "Reading the audio")
        turns = who_speaks_when(pipeline, voices.read_audio(source, RATE), people, job)
    if not turns:
        raise ToolError(f"Nobody could be heard speaking in {source.name}.")
    labelled = assign(lines, turns)

    # Written only now, all at once, so a stopped job leaves no half-written files.
    base = segments.name.removesuffix(".segments.json")
    name = paths.free_name(segments.parent, f"{base} (speakers)", [".txt", ".segments.json"])
    transcript, labelled_file = segments.parent / f"{name}.txt", segments.parent / f"{name}.segments.json"
    transcript.write_text("".join(f"[{line['start']:.1f}s] {line['speaker']}: {line['text']}\n" for line in labelled),
                          encoding="utf-8")
    labelled_file.write_text(json.dumps(labelled, ensure_ascii=False, indent=1), encoding="utf-8")
    seconds = {}
    for line in labelled:
        seconds[line["speaker"]] = seconds.get(line["speaker"], 0) + line["end"] - line["start"]
    job.report(100, "Speakers labelled")
    return {"transcript_file": str(transcript), "segments_file": str(labelled_file), "lines": len(labelled),
            "speakers": {who: round(s) for who, s in seconds.items()}}
