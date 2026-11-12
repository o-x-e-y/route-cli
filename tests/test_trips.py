import datetime as dt
import json
from pathlib import Path

import pytest

from route import cli, trips
from route.times import TZ

FIXTURES = Path(__file__).parent / "fixtures"
NOW = dt.datetime(2026, 11, 12, 12, 0, tzinfo=TZ)

DEPART = ["--from", "Pathé Eindhoven", "--to", "Pathé Tilburg Stappegoor",
          "--depart", "2026-11-14 15:35"]
ARRIVE = ["--from", "Pathé Tilburg Stappegoor", "--to", "Helmond", "--arrive", "2026-11-14 23:30"]


def run(capsys, fixture, argv):
    """Exit code, parsed --json output (or None), stderr, and the request bodies sent."""
    sent = []

    def fetch(body):
        sent.append(body)
        return json.loads((FIXTURES / f"{fixture}.json").read_text())

    code = cli.main([*argv, "--json"], fetch=fetch, now=NOW)
    out, err = capsys.readouterr()
    return code, json.loads(out) if out else None, err, sent


def test_depart_request(capsys):
    *_, sent = run(capsys, "eindhoven-stappegoor-depart", DEPART)
    assert sent == [{
        "origin": {"address": "Pathé Eindhoven"},
        "destination": {"address": "Pathé Tilburg Stappegoor"},
        "travelMode": "TRANSIT",
        "departureTime": "2026-11-14T15:35:00+01:00",
        "computeAlternativeRoutes": True,
        "languageCode": "nl",
    }]


def test_arrive_request(capsys):
    *_, sent = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    assert sent[0]["arrivalTime"] == "2026-11-14T23:30:00+01:00"
    assert "departureTime" not in sent[0]


def test_depart_options(capsys):
    code, result, _, _ = run(capsys, "eindhoven-stappegoor-depart", DEPART)
    assert code == 0
    assert result["depart"] == "2026-11-14T15:35:00+01:00"
    first = result["options"][0]
    assert first == {
        "depart": "2026-11-14T15:41:00+01:00",
        "arrive": "2026-11-14T16:54:00+01:00",
        "duration_min": 73,
        "transfers": 1,
        "wait_min": 9,
        "tightest_transfer_min": 9,
        "legs": [
            {"mode": "walk", "from": "Pathé Eindhoven", "to": "Eindhoven Centraal",
             "depart": "2026-11-14T15:41:00+01:00", "arrive": "2026-11-14T15:51:00+01:00",
             "duration_min": 10},
            {"mode": "train", "line": "Sprinter", "headsign": "Tilburg Universiteit",
             "operator": "Nederlandse Spoorwegen", "from": "Eindhoven Centraal", "to": "Tilburg",
             "depart": "2026-11-14T15:51:00+01:00", "arrive": "2026-11-14T16:20:00+01:00",
             "duration_min": 29},
            {"mode": "walk", "from": "Tilburg", "to": "Tilburg, Centraal Station",
             "depart": "2026-11-14T16:20:00+01:00", "arrive": "2026-11-14T16:25:00+01:00",
             "duration_min": 5},
            {"mode": "bus", "line": "1", "headsign": "ETZ Elisabeth", "operator": "Bravo (Arriva)",
             "from": "Tilburg, Centraal Station", "to": "Tilburg, Stappegoor/IJsbaan",
             "depart": "2026-11-14T16:34:00+01:00", "arrive": "2026-11-14T16:49:00+01:00",
             "duration_min": 15, "wait_min": 9},
            {"mode": "walk", "from": "Tilburg, Stappegoor/IJsbaan",
             "to": "Pathé Tilburg Stappegoor",
             "depart": "2026-11-14T16:49:00+01:00", "arrive": "2026-11-14T16:54:00+01:00",
             "duration_min": 5},
        ],
    }


def test_dominated_options_are_dropped(capsys):
    _, result, _, _ = run(capsys, "eindhoven-stappegoor-depart", DEPART)
    raw = json.loads((FIXTURES / "eindhoven-stappegoor-depart.json").read_text())
    assert len(raw["routes"]) == 6
    assert [(o["depart"][11:16], o["arrive"][11:16]) for o in result["options"]] == [
        ("15:41", "16:54"), ("16:04", "17:09")]


def test_walking_beats_waiting(capsys):
    """22:10 takes bus 1 from the door and waits 21 min in Tilburg; 22:15
    walks 15 min to bus 137 and arrives at the same time. Walking isn't a
    cost, so leaving later wins."""
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    times = [(o["depart"][11:16], o["arrive"][11:16]) for o in result["options"]]
    assert times == [("21:40", "22:58"), ("22:15", "23:28")]


def test_waits_and_tight_transfers(capsys):
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    option = result["options"][1]
    assert [leg.get("wait_min") for leg in option["legs"]] == [None, None, None, 10, 2]
    assert (option["wait_min"], option["tightest_transfer_min"]) == (12, 2)


def test_no_transfer_no_tightest(capsys):
    _, result, _, _ = run(capsys, "latlng-walk-only",
                          ["--from", "51.4794,5.6570", "--to", "Pathé Helmond",
                           "--depart", "2026-11-14 10:00"])
    assert result["options"][0]["wait_min"] == 0
    assert "tightest_transfer_min" not in result["options"][0]


def option(depart, arrive, transfers, *waits):
    legs = [{"mode": "train"}] + [{"mode": "train", "wait_min": w} for w in waits]
    return {"depart": f"2026-11-14T{depart}:00+01:00", "arrive": f"2026-11-14T{arrive}:00+01:00",
            "transfers": transfers, "legs": legs}


def test_a_tight_transfer_counts_against_an_option():
    safe, tight = option("16:00", "17:00", 1, 8), option("16:00", "17:00", 1, 2)
    assert trips._beats(safe, tight)
    assert not trips._beats(tight, safe)


def test_a_faster_tight_option_is_kept():
    safe, tight = option("16:00", "17:10", 1, 8), option("16:00", "17:00", 1, 2)
    assert not trips._beats(safe, tight)
    assert not trips._beats(tight, safe)


def test_arrive_options_arrive_in_time(capsys):
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    assert all(o["arrive"] <= "2026-11-14T23:30:00+01:00" for o in result["options"])


def test_utc_stamps_become_local_time(capsys):
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    bus = result["options"][0]["legs"][1]
    raw = (FIXTURES / "stappegoor-helmond-arrive.json").read_text()
    assert '"departureTime": "2026-11-14T20:44:00Z"' in raw
    assert (bus["line"], bus["depart"]) == ("1", "2026-11-14T21:44:00+01:00")


def test_same_station_transfer_has_no_walk(capsys):
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    modes = [leg["mode"] for leg in result["options"][1]["legs"]]
    assert modes == ["walk", "bus", "walk", "train", "train"]


def test_durations_add_up(capsys):
    for fixture, argv in (("eindhoven-stappegoor-depart", DEPART),
                          ("stappegoor-helmond-arrive", ARRIVE)):
        _, result, _, _ = run(capsys, fixture, argv)
        for option in result["options"]:
            start = dt.datetime.fromisoformat(option["depart"])
            end = dt.datetime.fromisoformat(option["arrive"])
            assert option["duration_min"] == (end - start).total_seconds() / 60
            assert option["legs"][0]["depart"] == option["depart"]
            assert option["legs"][-1]["arrive"] == option["arrive"]


def test_resolved_places(capsys):
    _, result, _, _ = run(capsys, "stappegoor-helmond-arrive", ARRIVE)
    assert result["from"] == {"query": "Pathé Tilburg Stappegoor", "lat": 51.539557,
                              "lng": 5.075946, "place_id": "ChIJg2kuiFC-xkcR9d4ABWTtpnk",
                              "types": ["establishment", "movie_theater", "point_of_interest"]}
    assert result["to"]["types"] == ["locality", "political"]


def test_maps_url_carries_place_ids(capsys):
    _, result, _, _ = run(capsys, "eindhoven-stappegoor-depart", DEPART)
    assert "origin_place_id=ChIJw6PJ3RzZxkcR6E-OfD8Td0I" in result["maps_url"]
    assert "destination_place_id=ChIJg2kuiFC-xkcR9d4ABWTtpnk" in result["maps_url"]


def test_address_not_found(capsys):
    code, result, err, _ = run(capsys, "address-not-found",
                               ["--from", "Xyzzyqplaats Nergensstraat 9999", "--to", "Helmond",
                                "--depart", "2026-11-14 15:35"])
    assert (code, result) == (1, None)
    assert err == ("route: Google could not find --from 'Xyzzyqplaats Nergensstraat 9999': "
                   "Address not found.\n")


def test_walk_only_starts_at_the_asked_time(capsys):
    _, result, _, sent = run(capsys, "latlng-walk-only",
                             ["--from", "51.4794,5.6570", "--to", "Pathé Helmond",
                              "--depart", "2026-11-14 10:00"])
    assert sent[0]["origin"] == {"location": {"latLng": {"latitude": 51.4794,
                                                         "longitude": 5.657}}}
    assert result["from"] == {"query": "51.4794,5.6570", "lat": 51.4794, "lng": 5.657}
    [option] = result["options"]
    assert (option["depart"], option["arrive"], option["transfers"]) == (
        "2026-11-14T10:00:00+01:00", "2026-11-14T10:08:00+01:00", 0)
    assert [leg["mode"] for leg in option["legs"]] == ["walk"]


def test_walk_only_arrive_counts_back(capsys):
    _, result, _, _ = run(capsys, "latlng-walk-only",
                          ["--from", "51.4794,5.6570", "--to", "Pathé Helmond",
                           "--arrive", "2026-11-14 10:00"])
    assert result["options"][0]["depart"] == "2026-11-14T09:52:00+01:00"


def test_no_routes(capsys):
    def fetch(body):
        return {"geocodingResults": {"origin": {"placeId": "a"}, "destination": {"placeId": "b"}}}

    assert cli.main(DEPART, fetch=fetch, now=NOW) == 1
    assert "no public transport route" in capsys.readouterr().err


@pytest.mark.parametrize("when", ["2027-02-21 10:00", "2026-11-04 10:00"])
def test_outside_googles_window_sends_nothing(capsys, when):
    sent = []
    assert cli.main(["--from", "a", "--to", "b", "--depart", when],
                    fetch=sent.append, now=NOW) == 1
    assert sent == []
    assert "7 days back and 100 days ahead" in capsys.readouterr().err
