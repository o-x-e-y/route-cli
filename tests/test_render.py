import datetime as dt
import json
from pathlib import Path

from route import cli
from route.times import TZ

FIXTURES = Path(__file__).parent / "fixtures"
NOW = dt.datetime(2026, 11, 12, 12, 0, tzinfo=TZ)


def text(capsys, fixture, argv):
    data = json.loads((FIXTURES / f"{fixture}.json").read_text())
    assert cli.main(argv, fetch=lambda body: data, now=NOW) == 0
    return capsys.readouterr().out


def test_text_summary(capsys):
    out = text(capsys, "eindhoven-stappegoor-depart",
               ["--from", "Pathé Eindhoven", "--to", "Pathé Tilburg Stappegoor",
                "--depart", "2026-11-14 15:35"])
    assert out.splitlines()[:10] == [
        "from: Pathé Eindhoven (51.440527,5.480802; movie_theater)",
        "to:   Pathé Tilburg Stappegoor (51.539557,5.075946; movie_theater)",
        "depart after Sat 2026-11-14 15:35",
        "",
        "1. 15:41 → 16:54  73 min, 1 transfer",
        "   15:41-15:51  walk 10 min to Eindhoven Centraal",
        "   15:51-16:20  train Sprinter (to Tilburg Universiteit): Eindhoven Centraal → Tilburg",
        "   16:20-16:25  walk 5 min to Tilburg, Centraal Station",
        "   16:34-16:49  bus 1 (to ETZ Elisabeth): Tilburg, Centraal Station → "
        "Tilburg, Stappegoor/IJsbaan",
        "   16:49-16:54  walk 5 min to Pathé Tilburg Stappegoor",
    ]
    assert out.rstrip().splitlines()[-1].startswith("maps: https://www.google.com/maps/dir/?api=1")


def test_typed_coordinates_are_not_repeated(capsys):
    out = text(capsys, "latlng-walk-only",
               ["--from", "51.4794,5.6570", "--to", "Pathé Helmond",
                "--depart", "2026-11-14 10:00"])
    assert out.splitlines()[0] == "from: 51.4794,5.6570"
    assert "0 transfers" in out


def test_next_day_is_marked(capsys):
    out = text(capsys, "latlng-walk-only",
               ["--from", "51.4794,5.6570", "--to", "Pathé Helmond",
                "--arrive", "2026-11-15 00:03"])
    assert "1. 23:55 (-1d) → 00:03  8 min" in out
