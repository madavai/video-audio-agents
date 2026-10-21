import pytest


@pytest.fixture(autouse=True)
def private_data(tmp_path, monkeypatch):
    """Every test gets its own empty data folder, so nothing touches the real models or log."""
    monkeypatch.setenv("VAA_DATA", str(tmp_path / "data"))
    return tmp_path / "data"
