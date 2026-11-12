import re

from .errors import RouteError

_LATLNG = re.compile(r"^\s*(-?\d{1,3}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")


def latlng(text: str) -> tuple[float, float] | None:
    """`lat,lng` as numbers, or None when the text is a name or address."""
    match = _LATLNG.match(text)
    if not match:
        return None
    lat, lng = float(match[1]), float(match[2])
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise RouteError(f"{text!r} is not a valid lat,lng")
    return lat, lng


def waypoint(text: str) -> dict:
    """The Google Routes `Waypoint` for what was typed after --from / --to."""
    if not text.strip():
        raise RouteError("empty place")
    if point := latlng(text):
        return {"location": {"latLng": {"latitude": point[0], "longitude": point[1]}}}
    return {"address": text.strip()}
