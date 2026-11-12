# route-cli

Door-to-door public transport options in the Netherlands, from the Google
Routes API. `README.md` is the user documentation (written for agents).
`PLAN.md` holds the original plan, the doc check and the possible later
sources (Transitous, NS).

## Using it

Run `route --help`. Prefer `--json`. Every call is one billed Google request:
don't scan times in a loop, and don't use the live API to test.

## Layout

| file | |
|---|---|
| `cli.py` | argparse surface; `plan()` ties the steps together |
| `times.py` | time parsing, all in Europe/Amsterdam |
| `places.py` | free text or `lat,lng` → Google waypoint |
| `google.py` | request body, field mask, HTTP and its errors |
| `trips.py` | response → options: times, legs, dropping dominated options |
| `render.py` | text and JSON output |
| `maps.py` | Google Maps directions links |

## Things the API does that are easy to get wrong

- Only transit steps have timestamps, and they're UTC (`Z`). Walking only
  has `staticDuration`. Depart/arrive are worked out from the walks around
  the first and last ride, which matches the route `duration` exactly.
- Up to 6 routes come back, more than the documented "default + 3".
- A same-station transfer is a 0 s walk.
- An unknown address is a `200` with `geocodingResults.<side>.geocoderStatus.code`
  set and no routes.
- There is no resolved place name, only `placeId` and `type`.
- A top-level `routingPreference` makes a transit request fail. Transit
  options go under `transitPreferences`.
- No caching or storing of results beyond one run (Google ToS). The
  fixtures are test data, not a cache.

## Working on it

`nix develop`, then `pytest` and `ruff check`. Offline only:
`tests/fixtures/` holds real responses recorded on 2026-11-12 with the
current field mask. If you change `FIELD_MASK`, re-record them; never put
the key in a fixture.
