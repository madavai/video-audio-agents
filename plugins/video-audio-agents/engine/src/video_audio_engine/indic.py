"""Kannada spoken directly in a saved voice by AI4Bharat's IndicF5 (F5-TTS taught Indian languages), in place of the
reader voice route. Installed only by the setup's Kannada voice option (install.py indic); its model is gated on
Hugging Face and downloaded with the person's key (models.INDIC). Runs on the processor.

IndicF5 copies a voice from a recording and the exact words said in it, so a voice needs one reading of
voices.SENTENCE (voices.keep_reading, checked by voices.says_sentence); a voice without one keeps the reader route.

Its makers call it MIT-licensed, but made it from F5-TTS's English model, whose weights are licensed for
non-commercial use only (CC BY-NC 4.0): the user guide, the changelog and the setup say so."""
import gc
import importlib.util

import numpy as np

from . import models, voices
from .paths import data_dir
from .speakers import printed_to_log

RATE = 24000
LONGEST = 22  # seconds F5 makes at once, the reading included; a longer text is made in parts
# F5's steps from noise to speech for each take. Its default is 32; measured on two FLEURS Kannada speakers (checklist
# 17), 16 sounded as much like them and its words were as clear, in half the time: about 9 seconds of work per
# second of speech on a 24-thread processor, against 19.
STEPS = 16


def installed() -> bool:
    try:
        return importlib.util.find_spec("f5_tts") is not None
    except ModuleNotFoundError:
        return False


def ready() -> bool:
    """Whether the Kannada voice can run: F5-TTS installed, and IndicF5 downloaded or the key to download it."""
    return installed() and (models.is_present("kannada") or (data_dir() / models.KEY_FILE).exists())


class Speaker:
    """IndicF5 used like the Chatterbox models: prepare_conditionals(reading), then generate(text) gives the text
    spoken in that voice, as a 1 x n tensor at `sr`."""
    sr = RATE

    def __init__(self, model, vocoder):
        self.model, self.vocoder, self.voice = model, vocoder, None

    def prepare_conditionals(self, reading) -> None:
        """At an even volume, as voices.sample does: F5 makes speech as loud as what it listens to."""
        import torch
        audio = voices.read_audio(reading, RATE)
        self.voice = torch.from_numpy(audio / (float(np.abs(audio).max()) or 1.0) * 0.9).unsqueeze(0)

    def generate(self, text: str, done=lambda share: None):
        """`done(share)` is called at each of F5's steps with the share of the text made so far (0 to 1): a take
        runs for minutes, so this keeps the progress moving, and Esc (raised from it) stops within seconds."""
        import torch
        from f5_tts.infer.utils_infer import chunk_text, infer_batch_process
        seconds = self.voice.shape[-1] / RATE
        # As F5's own infer_process: the bytes of text that fit in what is left of LONGEST, at the reading's pace.
        fits = int(len(voices.SENTENCE.encode("utf-8")) / seconds * (LONGEST - seconds))
        pieces, waves, passes = chunk_text(text, max_chars=fits), [], [0]

        def each_pass(*_):  # two passes of the model per step: with and without the voice and words to follow
            done(passes[0] / (2 * STEPS * len(pieces)))
            passes[0] += 1

        hook = self.model.transformer.register_forward_pre_hook(each_pass)
        try:
            with printed_to_log("IndicF5"):
                for piece in pieces:
                    wave, _, _ = next(infer_batch_process((self.voice, RATE), voices.SENTENCE, [piece], self.model,
                                                          self.vocoder, nfe_step=STEPS, progress=None, device="cpu"))
                    waves.append(wave)
        finally:
            hook.remove()
            self.model.transformer.clear_cache()  # F5 keeps the words' encoding between passes; stopped, it stays
        return torch.from_numpy(np.concatenate(waves).astype(np.float32)).unsqueeze(0)


def load(report) -> Speaker:
    """IndicF5, downloaded first if needed, built from its two files (the model and vocoder in model.safetensors,
    the letters it knows in vocab.txt), so F5-TTS never downloads anything itself. The big model in memory before
    is let go first."""
    if "kannada" not in models.loaded:
        models.ensure(["kannada"], report)
        models.loaded.clear()
        gc.collect()
        report(0, "Loading the Kannada voice model")
        with printed_to_log("IndicF5"):
            from f5_tts.model import CFM, DiT
            from f5_tts.model.utils import get_tokenizer
            from safetensors.torch import load_file
            from vocos import Vocos
            from vocos.feature_extractors import MelSpectrogramFeatures
            from vocos.heads import ISTFTHead
            from vocos.models import VocosBackbone
        folder = models.folder("kannada")
        letters, count = get_tokenizer(str(folder / "checkpoints" / "vocab.txt"), "custom")
        # F5-TTS's first "Base" design, which IndicF5 was made from, and the Vocos vocoder at 24 kHz.
        model = CFM(transformer=DiT(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, text_mask_padding=False,
                                    conv_layers=4, pe_attn_head=1, text_num_embeds=count, mel_dim=100),
                    mel_spec_kwargs=dict(n_fft=1024, hop_length=256, win_length=1024, n_mel_channels=100,
                                         target_sample_rate=RATE, mel_spec_type="vocos"),
                    odeint_kwargs=dict(method="euler"), vocab_char_map=letters)
        vocoder = Vocos(MelSpectrogramFeatures(sample_rate=RATE, n_fft=1024, hop_length=256, n_mels=100),
                        VocosBackbone(input_channels=100, dim=512, intermediate_dim=1536, num_layers=8),
                        ISTFTHead(dim=512, n_fft=1024, hop_length=256))
        weights = load_file(folder / "model.safetensors")
        for part, prefix in ((model, "ema_model._orig_mod."), (vocoder, "vocoder._orig_mod.")):
            part.load_state_dict({key.removeprefix(prefix): value for key, value in weights.items()
                                  if key.startswith(prefix)})
            part.eval()
        del weights
        models.loaded["kannada"] = Speaker(model, vocoder)
    return models.loaded["kannada"]
