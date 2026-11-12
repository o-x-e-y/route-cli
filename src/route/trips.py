"""Google Routes response -> the options this CLI prints.

Google gives timestamps only for transit steps. Walking has a duration and
nothing else, so the walk before the first vehicle is counted back from its
departure and the walk after the last one forward from its arrival. Walks are
rounded up to whole minutes, which keeps every time on the minute and errs on
the side of leaving early.
"""

import datetime as dt
import math

from .errors import RouteError
from .times import TZ

MODES = {
    "RAIL": "train", "HEAVY_RAIL": "train", "COMMUTER_TRAIN": "train",
    "HIGH_SPEED_TRAIN": "train", "LONG_DISTANCE_TRAIN": "train",
    "BUS": "bus", "INTERCITY_BUS": "bus", "TROLLEYBUS": "bus",
    "TRAM": "tram", "SUBWAY": "metro", "METRO_RAIL": "metro", "FERRY": "ferry",
}


def resolved(response: dict, side: str, query: str, location: dict | None) -> dict:
    """What `--from` (side "origin") or `--to` ("destination") turned into."""
    geocoded = response.get("geocodingResults", {}).get(side, {})
    status = geocoded.get("geocoderStatus", {})
    if status.get("code"):
        flag = "--from" if side == "origin" else "--to"
        raise RouteError(f"Google could not find {flag} {query!r}: "
                         f"{status.get('message', 'no match')}")
    place = {"query": query}
    if location:
        place["lat"] = round(location["latLng"]["latitude"], 6)
        place["lng"] = round(location["latLng"]["longitude"], 6)
    if "placeId" in geocoded:
        place["place_id"] = geocoded["placeId"]
        place["types"] = geocoded.get("type", [])
    return place


def options(response: dict, origin: str, destination: str, moment: dt.datetime, *,
            arrive: bool) -> list[dict]:
    found = [_option(route, origin, destination, moment, arrive)
             for route in response.get("routes", [])]
    kept = [o for o in found if not any(_beats(other, o) for other in found)]
    return sorted(_unique(kept), key=lambda o: (o["depart"], o["arrive"]))


def _cost(option):
    walk = sum(leg["duration_min"] for leg in option["legs"] if leg["mode"] == "walk")
    return (-dt.datetime.fromisoformat(option["depart"]).timestamp(),
            dt.datetime.fromisoformat(option["arrive"]).timestamp(), option["transfers"], walk)


def _beats(a, b):
    """`a` leaves no earlier, arrives no later, and has no more transfers or
    walking than `b`, and is better on at least one of those."""
    ca, cb = _cost(a), _cost(b)
    return ca != cb and all(x <= y for x, y in zip(ca, cb, strict=True))


def _unique(found):
    return list({repr(o): o for o in found}.values())


def _option(route, origin, destination, moment, arrive):
    steps = [step for leg in route.get("legs", []) for step in leg.get("steps", [])]
    legs = _group(steps)
    rides = [leg for leg in legs if leg["mode"] != "walk"]
    if rides:
        cursor = rides[0]["depart"] - sum((leg["duration"] for leg in legs[:legs.index(rides[0])]),
                                          dt.timedelta())
    else:
        total = dt.timedelta(minutes=_minutes(_seconds(route.get("duration"))))
        cursor = moment - total if arrive else moment
    for i, leg in enumerate(legs):
        if leg["mode"] == "walk":
            leg["from"] = legs[i - 1]["to"] if i else origin
            leg["to"] = legs[i + 1]["from"] if i + 1 < len(legs) else destination
            leg["depart"], leg["arrive"] = cursor, cursor + leg.pop("duration")
        cursor = leg["arrive"]
    depart, end = (legs[0]["depart"], legs[-1]["arrive"]) if legs else (cursor, cursor)
    return {
        "depart": _iso(depart),
        "arrive": _iso(end),
        "duration_min": _span(depart, end),
        "transfers": max(len(rides) - 1, 0),
        "legs": [_finish(leg) for leg in legs],
    }


def _group(steps):
    """Runs of walking steps become one walk leg; each transit step is a leg."""
    legs = []
    for step in steps:
        if step.get("travelMode") == "TRANSIT" and "transitDetails" in step:
            legs.append(_ride(step["transitDetails"]))
            continue
        seconds = _seconds(step.get("staticDuration"))
        if legs and legs[-1]["mode"] == "walk":
            legs[-1]["seconds"] += seconds
        else:
            legs.append({"mode": "walk", "seconds": seconds})
    for leg in legs:
        if leg["mode"] == "walk":
            leg["duration"] = dt.timedelta(minutes=_minutes(leg.pop("seconds")))
    return [leg for leg in legs if leg["mode"] != "walk" or leg["duration"]]


def _ride(transit):
    stops, line = transit["stopDetails"], transit.get("transitLine", {})
    vehicle = line.get("vehicle", {}).get("type", "OTHER")
    ride = {
        "mode": MODES.get(vehicle, vehicle.lower()),
        "line": line.get("nameShort") or line.get("name", ""),
        "headsign": transit.get("headsign", ""),
        "operator": ", ".join(a["name"] for a in line.get("agencies", []) if a.get("name")),
        "from": stops["departureStop"]["name"],
        "to": stops["arrivalStop"]["name"],
        "depart": _local(stops["departureTime"]),
        "arrive": _local(stops["arrivalTime"]),
    }
    return {k: v for k, v in ride.items() if v != ""}


def _finish(leg):
    out = {k: v for k, v in leg.items() if k not in ("depart", "arrive")}
    out["depart"], out["arrive"] = _iso(leg["depart"]), _iso(leg["arrive"])
    out["duration_min"] = _span(leg["depart"], leg["arrive"])
    return out


def _seconds(duration: str | None) -> int:
    return int(float(duration.rstrip("s"))) if duration else 0


def _minutes(seconds: int) -> int:
    return math.ceil(seconds / 60)


def _span(start: dt.datetime, end: dt.datetime) -> int:
    return round((end - start).total_seconds() / 60)


def _local(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp).astimezone(TZ)


def _iso(moment: dt.datetime) -> str:
    return moment.isoformat(timespec="seconds")
