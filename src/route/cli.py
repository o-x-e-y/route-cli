import argparse
import sys

from . import config, places, times
from .errors import RouteError

EPILOG = f"""\
times: {times.FORMS}. Always local time, Europe/Amsterdam.
--arrive plans backwards: the options arrive at or before that time.

places: a place name, address or station as free text, or 'lat,lng'.

examples:
  route --from "Pathé Eindhoven" --to "Pathé Tilburg Stappegoor" --depart "2026-11-14 15:35" --json
  route --from "Pathé Tilburg Stappegoor" --to Helmond --arrive "2026-11-14 23:30" --json
  route --from 51.4416,5.4697 --to "Tilburg" --depart "tomorrow 09:00"

key: the Google Maps Platform key is read from {config.DEFAULT_GOOGLE_KEY_FILE},
or from the file $ROUTE_GOOGLE_KEY_FILE names.
"""


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


def run(args) -> str:
    places.waypoint(args.origin)
    places.waypoint(args.destination)
    times.parse_moment(args.depart or args.arrive)
    config.google_key()
    raise RouteError("routing is not built yet: Google Routes is step 2 of PLAN.md")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(run(args))
    except RouteError as error:
        print(f"route: {error}", file=sys.stderr)
        return 1
    return 0
