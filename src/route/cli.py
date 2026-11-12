import argparse
import datetime as dt
import sys
from collections.abc import Callable

from . import config, google, maps, render, times, trips, usage
from .errors import RouteError

EPILOG = f"""\
times: {times.FORMS}. Always local time, Europe/Amsterdam.
--arrive plans backwards: the options arrive at or before that time.

places: a place name, address or station as free text, or 'lat,lng'.

examples:
  route --from "Pathé Eindhoven" --to "Pathé Tilburg Stappegoor" --depart "2026-11-14 15:35" --json
  route --from "Pathé Tilburg Stappegoor" --to Helmond --arrive "2026-11-14 23:30" --json
  route --from 51.4416,5.4697 --to "Tilburg" --depart "tomorrow 09:00"

One Google Routes request per call, billed: don't loop over many times when
one --depart or --arrive answers the question.

setup: $ROUTE_GOOGLE_KEY_FILE names the file holding the Google Maps Platform key
(Routes API). At most $ROUTE_MAX_REQUESTS requests (default {config.DEFAULT_MAX_REQUESTS}) are sent
per $ROUTE_LIMIT_DAYS days (default {config.DEFAULT_LIMIT_DAYS}); the times of past requests are
kept in $XDG_STATE_HOME/route/requests.json.
"""

Fetch = Callable[[dict], dict]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="route", description="Public transport options in the Netherlands, door to door.",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="origin", required=True, metavar="PLACE")
    parser.add_argument("--to", dest="destination", required=True, metavar="PLACE")
    when = parser.add_mutually_exclusive_group(required=True)
    when.add_argument("--depart", metavar="TIME", help="leave at or after TIME")
    when.add_argument("--arrive", metavar="TIME", help="arrive at or before TIME")
    parser.add_argument("--json", action="store_true", help="JSON output, for agents")
    return parser


def plan(args, fetch: Fetch, now: dt.datetime) -> dict:
    arrive = args.arrive is not None
    moment = times.parse_moment(args.arrive or args.depart, now=now.date())
    google.check_window(moment, now)
    response = fetch(google.request_body(args.origin, args.destination, moment, arrive=arrive))

    first = (response.get("routes") or [{}])[0].get("legs") or [{}]
    origin = trips.resolved(response, "origin", args.origin,
                            _typed(args.origin) or first[0].get("startLocation"))
    destination = trips.resolved(response, "destination", args.destination,
                                 _typed(args.destination) or first[-1].get("endLocation"))
    found = trips.options(response, args.origin, args.destination, moment, arrive=arrive)
    if not found:
        raise RouteError(f"Google found no public transport route from {args.origin!r} "
                         f"to {args.destination!r} around {times.rfc3339(moment)}")
    return {
        "from": origin,
        "to": destination,
        "arrive" if arrive else "depart": times.rfc3339(moment),
        "maps_url": maps.maps_url(args.origin, args.destination,
                                  origin_place_id=origin.get("place_id"),
                                  destination_place_id=destination.get("place_id")),
        "options": found,
    }


def _typed(text: str) -> dict | None:
    point = google.places.latlng(text)
    return {"latLng": {"latitude": point[0], "longitude": point[1]}} if point else None


def _google(body: dict) -> dict:
    key = config.google_key()
    max_requests, days = config.limit()
    usage.spend(config.state_dir() / "requests.json", max_requests, days,
                dt.datetime.now(dt.UTC))
    return google.compute_routes(key, body)


def main(argv=None, fetch: Fetch = _google, now: dt.datetime | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = plan(args, fetch, now or dt.datetime.now(times.TZ))
    except RouteError as error:
        print(f"route: {error}", file=sys.stderr)
        return 1
    print(render.as_json(result) if args.json else render.as_text(result))
    return 0
