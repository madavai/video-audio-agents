from video_audio_engine import models

GB = 1024**3


def test_every_setup_model_is_in_the_table():
    for name in models.FULL:
        model = models.MODELS[name]
        repo, revision = model["repo"]
        assert "/" in repo and len(revision) == 40  # pinned to an exact version
        assert model["label"] and all(size > 0 for size in model["files"].values())


def test_standard_is_part_of_full():
    assert set(models.STANDARD) <= set(models.FULL)


def test_missing_gb_counts_each_file_once():
    voice = sum(models.MODELS["voice"]["files"].values())
    english = sum(models.MODELS["english"]["files"].values())
    shared = models.MODELS["voice"]["files"]["s3gen.safetensors"] + models.MODELS["voice"]["files"]["conds.pt"]
    assert models.missing_gb(["voice"]) == round(voice / GB, 1)
    assert models.missing_gb(["voice", "english"]) == round((voice + english - shared) / GB, 1)


def test_a_file_of_the_wrong_size_counts_as_missing():
    files = models.MODELS["base"]["files"]
    for file, size in files.items():
        path = models.folder("base") / file
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(size)
    assert models.is_present("base")
    with open(models.folder("base") / "model.bin", "ab") as f:
        f.truncate(10)  # a half-written file
    assert not models.is_present("base")
    assert list(models.missing_files(["base"])) == [models.folder("base") / "model.bin"]


def test_model_urls_point_at_the_pinned_version():
    url, size = next(iter(models.missing_files(["small"]).values()))
    assert url.startswith("https://huggingface.co/Systran/faster-whisper-small/resolve/536b066")
    assert size > 0
