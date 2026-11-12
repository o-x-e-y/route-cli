import datetime as dt
import json

from .places import latlng

GENERIC_TYPES = {"establishment", "point_of_interest", "political", "geocode"}


def as_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


def as_text(result: dict) -> str:
    when = "arrive" if "arrive" in result else "depart"
    asked = dt.datetime.fromisoformat(result[when])
    lines = [
        f"from: {_place(result['from'])}",
        f"to:   {_place(result['to'])}",
        f"{'arrive by' if when == 'arrive' else 'depart after'} "
        f"{asked:%a %Y-%m-%d %H:%M}",
    ]
    for n, option in enumerate(result["options"], 1):
        transfers = option["transfers"]
        lines += ["", f"{n}. {_time(option['depart'], asked)} → {_time(option['arrive'], asked)}  "
                      f"{option['duration_min']} min, {transfers} "
                      f"transfer{'' if transfers == 1 else 's'}"]
        lines += [f"   {_leg(leg, asked)}" for leg in option["legs"]]
    lines += ["", f"maps: {result['maps_url']}"]
    return "\n".join(lines)


def _place(place: dict) -> str:
    out = place["query"]
    details = []
    if "lat" in place and not latlng(out):
        details.append(f"{place['lat']},{place['lng']}")
    specific = [t for t in place.get("types", []) if t not in GENERIC_TYPES]
    if specific:
        details.append(specific[0])
    return f"{out} ({'; '.join(details)})" if details else out


def _leg(leg: dict, asked: dt.datetime) -> str:
    span = f"{_time(leg['depart'], asked)}-{_time(leg['arrive'], asked)}"
    if leg["mode"] == "walk":
        return f"{span}  walk {leg['duration_min']} min to {leg['to']}"
    line = " ".join(filter(None, [leg["mode"], leg.get("line")]))
    headsign = f" (to {leg['headsign']})" if leg.get("headsign") else ""
    return f"{span}  {line}{headsign}: {leg['from']} → {leg['to']}"


def _time(stamp: str, asked: dt.datetime) -> str:
    moment = dt.datetime.fromisoformat(stamp)
    days = (moment.date() - asked.date()).days
    return f"{moment:%H:%M}" + (f" ({days:+d}d)" if days else "")
