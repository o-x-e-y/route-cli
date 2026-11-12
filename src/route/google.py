import datetime as dt
import json
import urllib.error
import urllib.request

from . import places, times
from .errors import RouteError

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

FIELD_MASK = ",".join([
    "routes.duration",
    "routes.legs.startLocation",
    "routes.legs.endLocation",
    "routes.legs.steps.travelMode",
    "routes.legs.steps.staticDuration",
    "routes.legs.steps.transitDetails",
    "geocodingResults",
])

# What Google's transit timetables cover, per the Routes docs.
PAST = dt.timedelta(days=7)
FUTURE = dt.timedelta(days=100)


def request_body(origin: str, destination: str, moment: dt.datetime, *, arrive: bool) -> dict:
    return {
        "origin": places.waypoint(origin),
        "destination": places.waypoint(destination),
        "travelMode": "TRANSIT",
        "arrivalTime" if arrive else "departureTime": times.rfc3339(moment),
        "computeAlternativeRoutes": True,
        "languageCode": "nl",
    }


def check_window(moment: dt.datetime, now: dt.datetime) -> None:
    if not now - PAST <= moment <= now + FUTURE:
        raise RouteError(f"{times.rfc3339(moment)} is outside what Google plans: "
                         "at most 7 days back and 100 days ahead")


def compute_routes(key: str, body: dict) -> dict:
    request = urllib.request.Request(
        URL, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key,
                 "X-Goog-FieldMask": FIELD_MASK})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise RouteError("Google quota reached; not retrying") from None
        raise RouteError(f"Google Routes answered {error.code}: {_message(error)}") from None
    except (urllib.error.URLError, TimeoutError) as error:
        raise RouteError(f"network error: {getattr(error, 'reason', error)}") from None


def _message(error: urllib.error.HTTPError) -> str:
    try:
        body = json.load(error)
    except ValueError:
        return error.reason
    status = body.get("error", body) if isinstance(body, dict) else {}
    return status.get("message") or error.reason
