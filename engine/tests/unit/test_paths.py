from pathlib import Path

from video_audio_engine import paths


def test_free_path_adds_a_number_instead_of_overwriting(tmp_path):
    first = paths.free_path(tmp_path, "Lesson", ".mp3")
    assert first == tmp_path / "Lesson.mp3"
    first.write_text("x")
    second = paths.free_path(tmp_path, "Lesson", ".mp3")
    assert second == tmp_path / "Lesson (2).mp3"
    second.write_text("x")
    assert paths.free_path(tmp_path, "Lesson", ".mp3") == tmp_path / "Lesson (3).mp3"
    assert paths.free_path(tmp_path, "Lesson", ".txt") == tmp_path / "Lesson.txt"


def test_safe_name_removes_forbidden_characters_and_limits_length():
    assert paths.safe_name('What: is "AI"? <part 1/2>') == "What is AI part 12"
    assert paths.safe_name("   ") == "untitled"
    assert paths.safe_name("dots at the end...") == "dots at the end"
    assert len(paths.safe_name("x" * 200)) == 80


def test_data_dir_comes_from_the_plugin(private_data):
    assert paths.data_dir() == private_data
    assert private_data.is_dir()


def test_data_dir_falls_back_when_claude_code_did_not_fill_it_in(monkeypatch, tmp_path):
    monkeypatch.setenv("VAA_DATA", "${CLAUDE_PLUGIN_DATA}")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert paths.data_dir() == tmp_path / ".claude" / "plugins" / "data" / "video-audio-agents-madavai"


def test_output_root_is_in_documents():
    assert paths.output_root().name == "VideoAudioAgents"
    assert paths.output_root().parent == paths.documents_dir()
