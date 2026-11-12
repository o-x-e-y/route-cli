import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("ROUTE_GOOGLE_KEY_FILE", str(tmp_path / "absent"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.delenv("ROUTE_MAX_REQUESTS", raising=False)
    monkeypatch.delenv("ROUTE_LIMIT_DAYS", raising=False)
