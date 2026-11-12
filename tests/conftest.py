import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def _no_real_key(monkeypatch, tmp_path):
    monkeypatch.setenv("ROUTE_GOOGLE_KEY_FILE", str(tmp_path / "absent"))
