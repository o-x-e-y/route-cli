"""Google Routes response -> the options this CLI prints.

Google gives timestamps only for transit steps. Walking has a duration and
nothing else, so the walk before the first vehicle is counted back from its
departure and the walk after the last one forward from its arrival. Walks are
rounded up to whole minutes, which keeps every time on the minute and errs on
the side of leaving early.

Walking costs the user nothing, but waiting does, and a tight transfer is a
risk: one minute of delay can mean the next connection is gone. So options
are compared on time, transfers and tight transfers, never on walking.
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

TIGHT_TRANSFER_MIN = 5


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
    tight = sum(1 for leg in option["legs"] if leg.get("wait_min", TIGHT_TRANSFER_MIN)
                < TIGHT_TRANSFER_MIN)
    return (-dt.datetime.fromisoformat(option["depart"]).timestamp(),
            dt.datetime.fromisoformat(option["arrive"]).timestamp(), option["transfers"], tight)


def _beats(a, b):
    """`a` leaves no earlier, arrives no later, and has no more transfers or
    tight transfers than `b`, and is better on at least one of those."""
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
            following = legs[i + 1] if i + 1 < len(legs) else None
            leg["from"] = legs[i - 1]["to"] if i else origin
            leg["to"] = following["from"] if following else destination
            leg["depart"], leg["arrive"] = cursor, cursor + leg.pop("duration")
            if following:
                # Rounding up can carry a walk past the departure Google fitted it to.
                leg["arrive"] = min(leg["arrive"], following["depart"])
        elif leg is not rides[0]:
            leg["wait"] = leg["depart"] - cursor
        cursor = leg["arrive"]
    depart, end = (legs[0]["depart"], legs[-1]["arrive"]) if legs else (cursor, cursor)
    waits = [_span(dt.timedelta(), leg["wait"]) for leg in legs if "wait" in leg]

    def total(mode_is_walk):
        return sum(_span(leg["depart"], leg["arrive"]) for leg in legs
                   if (leg["mode"] == "walk") == mode_is_walk)

    option = {
        "depart": _iso(depart),
        "arrive": _iso(end),
        "duration_min": _span(depart, end),
        "ride_min": total(False),
        "wait_min": sum(waits),
        "walk_min": total(True),
        "transfers": max(len(rides) - 1, 0),
    }
    if waits:
        option["tightest_transfer_min"] = min(waits)
    option["legs"] = [_finish(leg) for leg in legs]
    return option


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
    out = {k: v for k, v in leg.items() if k not in ("depart", "arrive", "wait")}
    out["depart"], out["arrive"] = _iso(leg["depart"]), _iso(leg["arrive"])
    out["duration_min"] = _span(leg["depart"], leg["arrive"])
    if "wait" in leg:
        out["wait_min"] = _span(dt.timedelta(), leg["wait"])
    return out


def _seconds(duration: str | None) -> int:
    return int(float(duration.rstrip("s"))) if duration else 0


def _minutes(seconds: int) -> int:
    return math.ceil(seconds / 60)


def _span(start, end) -> int:
    return round((end - start).total_seconds() / 60)


def _local(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp).astimezone(TZ)


def _iso(moment: dt.datetime) -> str:
    return moment.isoformat(timespec="seconds")
