"""Dubs that keep the original music and sound effects. The original sound stays wherever nobody speaks; under the
spoken lines the voice is taken out of it by HTDemucs (the Demucs music separator), so the music plays on under the
dub."""
import gc
import re

import numpy as np
import soundfile

from . import models, voices
from .texts import read_json

RATE = 44100  # HTDemucs works on 44.1 kHz stereo
PIECE, OVERLAP = 300, 10  # seconds: a long video is worked on in pieces that fade into each other, to save memory
PAD, FADE = 0.25, 0.25  # seconds: a voice may start or end a little outside its line's times


def under_dub(report, video, dub, segments_file, into) -> None:
    """Saves the sound for a dubbed video as a .wav at `into`: the original where nobody speaks, its music and sound
    effects without the voice under the lines of the segments file, and the dub on top."""
    lines = read_json(segments_file.read_text(encoding="utf-8"), segments=True)
    lines = [line for line in lines if re.search(r"\w", line["text"])]  # a "…" over music isn't spoken
    sound = voices.read_audio(video, RATE, channels=2)
    sound -= voice_in(sound, report) * (1 - kept(lines, len(sound)))[:, None]
    spoken = voices.read_audio(dub, RATE, channels=2)
    if len(spoken) > len(sound):  # the video's own sound ended early; the video's length is kept when merging
        sound = np.pad(sound, ((0, len(spoken) - len(sound)), (0, 0)))
    sound[:len(spoken)] += spoken
    sound *= min(1.0, 0.99 / max(float(np.abs(sound).max()), 1e-9))  # quieter rather than distorted
    soundfile.write(into, sound, RATE, subtype="PCM_16")


def kept(lines: list, length: int) -> np.ndarray:
    """1 where the original sound stays, 0 under the spoken lines (and PAD around them), with a FADE in between."""
    keep = np.ones(length, np.float32)
    for line in lines:
        start, end = line["start"] - PAD, line["end"] + PAD
        first, last = max(0, int((start - FADE) * RATE)), min(length, int((end + FADE) * RATE) + 1)
        t = np.arange(first, last) / RATE
        keep[first:last] = np.minimum(keep[first:last], np.clip(np.maximum(start - t, t - end) / FADE, 0, 1))
    return keep


def voice_in(sound: np.ndarray, report) -> np.ndarray:
    """The voices in the sound (rows of [left, right] at RATE), as HTDemucs hears them."""
    import torch
    from demucs.apply import apply_model

    model = load(report)
    mono = sound.mean(1)
    mean, std = float(mono.mean()), float(mono.std()) or 1.0  # the model expects the sound evened out like this
    voice, step, overlap = np.zeros_like(sound), (PIECE - OVERLAP) * RATE, OVERLAP * RATE
    fade = np.linspace(0, 1, overlap, dtype=np.float32)[:, None]
    for start in range(0, len(sound), step):
        def progress(state, start=start):  # once per 6 seconds of sound; on Esc, report stops the work
            if state["state"] == "end":
                done = start + state["segment_offset"]
                report(done / len(sound) * 100, "Taking the voice out of the original sound")

        piece = torch.from_numpy(np.ascontiguousarray((sound[start:start + PIECE * RATE].T - mean) / std))
        with torch.no_grad():
            found = apply_model(model, piece[None], shifts=0, callback=progress)[0, model.sources.index("vocals")]
        found = found.numpy().T * std
        if start:
            found[:overlap] = voice[start:start + overlap] * (1 - fade) + found[:overlap] * fade
        voice[start:start + len(found)] = found
        if start + PIECE * RATE >= len(sound):
            break
    return voice


def load(report):
    """HTDemucs, downloaded first if needed. Whatever big model was in memory before is let go first."""
    if "music" not in models.loaded:
        models.ensure(["music"], report)
        models.loaded.clear()
        gc.collect()
        report(0, "Loading the music keeper")
        from demucs.hf import load_safetensors_model
        models.loaded["music"] = load_safetensors_model(models.folder("music") / "955717e8.safetensors").eval()
    return models.loaded["music"]
