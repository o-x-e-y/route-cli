import pytest

from route import config
from route.cli import main
from route.errors import RouteError


def test_needs_depart_or_arrive():
    with pytest.raises(SystemExit) as exit_:
        main(["--from", "Helmond", "--to", "Tilburg"])
    assert exit_.value.code == 2


def test_not_both_depart_and_arrive():
    with pytest.raises(SystemExit) as exit_:
        main(["--from", "a", "--to", "b", "--depart", "today 10:00", "--arrive", "today 11:00"])
    assert exit_.value.code == 2


def test_bad_time_is_reported(capsys):
    assert main(["--from", "a", "--to", "b", "--depart", "soon"]) == 1
    assert capsys.readouterr().err.startswith("route: bad time 'soon'")



def test_key_is_read_and_stripped(monkeypatch, tmp_path):
    (tmp_path / "key").write_text("abc123\n")
    monkeypatch.setenv("ROUTE_GOOGLE_KEY_FILE", str(tmp_path / "key"))
    assert config.google_key() == "abc123"


def test_empty_key_file(monkeypatch, tmp_path):
    (tmp_path / "key").write_text("\n")
    monkeypatch.setenv("ROUTE_GOOGLE_KEY_FILE", str(tmp_path / "key"))
    with pytest.raises(RouteError, match="empty"):
        config.google_key()


def test_no_key_path_set(monkeypatch):
    monkeypatch.delenv("ROUTE_GOOGLE_KEY_FILE")
    with pytest.raises(RouteError, match=r"set \$ROUTE_GOOGLE_KEY_FILE"):
        config.google_key()


def test_missing_key_names_the_file(capsys, tmp_path):
    assert main(["--from", "a", "--to", "b", "--depart", "tomorrow 15:35"]) == 1
    err = capsys.readouterr().err
    assert str(tmp_path / "absent") in err and "ROUTE_GOOGLE_KEY_FILE" in err
