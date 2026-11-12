import datetime as dt
import json

import pytest

from route import cli, config, google
from route.errors import RouteError
from route.usage import spend

NOW = dt.datetime(2026, 11, 12, 12, 0, tzinfo=dt.UTC)


def test_counts_each_request(tmp_path):
    log = tmp_path / "requests.json"
    spend(log, 2, 7, NOW)
    spend(log, 2, 7, NOW + dt.timedelta(minutes=1))
    assert json.loads(log.read_text()) == ["2026-11-12T12:00:00+00:00", "2026-11-12T12:01:00+00:00"]


def test_refuses_a_full_window_and_says_when_it_frees_up(tmp_path):
    log = tmp_path / "requests.json"
    spend(log, 2, 7, NOW)
    spend(log, 2, 7, NOW + dt.timedelta(hours=1))
    with pytest.raises(RouteError, match="2 Google requests per 7 days") as error:
        spend(log, 2, 7, NOW + dt.timedelta(days=1))
    assert "allowed from 2026-11-19 13:00" in str(error.value)
    assert len(json.loads(log.read_text())) == 2


def test_old_requests_fall_out_of_the_window(tmp_path):
    log = tmp_path / "requests.json"
    spend(log, 1, 7, NOW)
    spend(log, 1, 7, NOW + dt.timedelta(days=7, seconds=1))
    assert json.loads(log.read_text()) == ["2026-11-19T12:00:01+00:00"]


def test_broken_log_is_not_silently_reset(tmp_path):
    log = tmp_path / "requests.json"
    log.write_text("{oops")
    with pytest.raises(RouteError, match="not a list of request times"):
        spend(log, 5, 7, NOW)


def test_limit_from_environment(monkeypatch):
    assert config.limit() == (600, 7)
    monkeypatch.setenv("ROUTE_MAX_REQUESTS", "50")
    monkeypatch.setenv("ROUTE_LIMIT_DAYS", "1")
    assert config.limit() == (50, 1)
    monkeypatch.setenv("ROUTE_MAX_REQUESTS", "lots")
    with pytest.raises(RouteError, match="whole number"):
        config.limit()


def test_cli_stops_before_sending(monkeypatch, tmp_path, capsys):
    (tmp_path / "key").write_text("k")
    monkeypatch.setenv("ROUTE_GOOGLE_KEY_FILE", str(tmp_path / "key"))
    monkeypatch.setenv("ROUTE_MAX_REQUESTS", "1")
    sent = []
    monkeypatch.setattr(google, "compute_routes", lambda key, body: sent.append(body) or {})
    argv = ["--from", "a", "--to", "b", "--depart", "tomorrow 10:00"]
    assert cli.main(argv) == 1
    assert "no public transport route" in capsys.readouterr().err
    assert cli.main(argv) == 1
    assert "local limit reached" in capsys.readouterr().err
    assert len(sent) == 1
    assert (tmp_path / "state" / "route" / "requests.json").exists()
