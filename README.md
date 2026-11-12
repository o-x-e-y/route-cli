# route

Public transport options in the Netherlands, door to door: **from X to Y,
leaving at or arriving by T, what are the options?** Train, bus, tram, metro
and the walks in between, in one answer, from Google's timetables.

It plans trips in advance. It gives no platforms, live delays or
disruptions, and it doesn't check whether a trip fits your schedule: you do
that with its output.

```sh
route --from "Pathé Eindhoven" --to "Pathé Tilburg Stappegoor" --depart "2026-11-14 15:35" --json
route --from "Pathé Tilburg Stappegoor" --to Helmond --arrive "2026-11-14 23:30" --json
```

## Flags

| flag | |
|---|---|
| `--from PLACE`, `--to PLACE` | free text (place name, address, station, town) or `lat,lng` |
| `--depart TIME` | options leaving at or after TIME |
| `--arrive TIME` | options arriving at or before TIME. Plans **backwards** from a fixed time: use it when something starts at T (a film, a shift), or for the last train home |
| `--json` | JSON output. Use this. Without it you get a short text summary |

Exactly one of `--depart` / `--arrive`. TIME is local time
(Europe/Amsterdam) as `'DATE HH:MM'`, with DATE as `YYYY-MM-DD`, `MM-DD`,
`DD` (the next such date), `today`, `tomorrow` or `+N` days. Google only
plans from 7 days back to 100 days ahead.

Every call is one billed Google request. Ask once with the time that
matters rather than scanning many times.

## JSON

```json
{
  "from": {"query": "Pathé Eindhoven", "lat": 51.440527, "lng": 5.480802,
           "place_id": "ChIJw6PJ3RzZxkcR6E-OfD8Td0I",
           "types": ["establishment", "movie_theater", "point_of_interest"]},
  "to": {"query": "Pathé Tilburg Stappegoor", "lat": 51.539557, "lng": 5.075946,
         "place_id": "ChIJg2kuiFC-xkcR9d4ABWTtpnk", "types": ["establishment", "movie_theater", "point_of_interest"]},
  "depart": "2026-11-14T15:35:00+01:00",
  "maps_url": "https://www.google.com/maps/dir/?api=1&origin=...&destination=...&travelmode=transit&...",
  "options": [
    {
      "depart": "2026-11-14T15:41:00+01:00",
      "arrive": "2026-11-14T16:54:00+01:00",
      "duration_min": 73,
      "transfers": 1,
      "wait_min": 9,
      "tightest_transfer_min": 9,
      "legs": [
        {"mode": "walk", "from": "Pathé Eindhoven", "to": "Eindhoven Centraal",
         "depart": "2026-11-14T15:41:00+01:00", "arrive": "2026-11-14T15:51:00+01:00", "duration_min": 10},
        {"mode": "train", "line": "Sprinter", "headsign": "Tilburg Universiteit",
         "operator": "Nederlandse Spoorwegen", "from": "Eindhoven Centraal", "to": "Tilburg",
         "depart": "2026-11-14T15:51:00+01:00", "arrive": "2026-11-14T16:20:00+01:00", "duration_min": 29},
        {"mode": "walk", "from": "Tilburg", "to": "Tilburg, Centraal Station", "...": "..."},
        {"mode": "bus", "line": "1", "headsign": "ETZ Elisabeth", "operator": "Bravo (Arriva)",
         "from": "Tilburg, Centraal Station", "to": "Tilburg, Stappegoor/IJsbaan", "...": "...",
         "wait_min": 9},
        {"mode": "walk", "from": "Tilburg, Stappegoor/IJsbaan", "to": "Pathé Tilburg Stappegoor", "...": "..."}
      ]
    }
  ]
}
```

- `from` / `to` show what the free text resolved to. There is no resolved
  name, so check `types`, the coordinates, and the first and last stop in
  the legs. A `locality` when you meant a building means it matched the
  town. "Eindhoven Centraal" matches a `bar` near the station, while
  "Station Eindhoven Centraal" gives the `train_station`. When `types` is
  not what you meant, ask again with a more specific name or `lat,lng`.
  `lat` / `lng` may be snapped to the nearest road. `place_id` and `types`
  are missing for `lat,lng` input.
- `depart` or `arrive` at the top level is the time you asked for.
- `options` are sorted by departure. An option is left out when another one
  leaves no earlier, arrives no later, and has no more transfers and no
  more tight transfers (under 5 minutes). Walking doesn't count: leaving
  later and walking to a stop beats waiting at one. What remains are real
  trade-offs, so pick by what matters for the trip.
- Option `depart` is when to leave the starting point, walk included.
  `arrive` is when you reach the destination, walk included.
- `mode` is `walk`, `train`, `bus`, `tram`, `metro`, `ferry`, or Google's
  vehicle type in lower case for anything rarer. `line` is the product for
  trains (`Intercity`, `Sprinter`) and the line number for buses and trams.
  `headsign` is the direction shown on the vehicle. `operator` can be
  foreign: `De Lijn` is a Belgian bus.
- `wait_min` on a ride is the time spent waiting for it after the previous
  ride and any walk in between. On the option it's the total.
  `tightest_transfer_min` is the shortest of those waits, and is missing
  when there is no transfer. Under 5 minutes, one minute of delay can cost
  the connection.
- All times are ISO 8601 with the Amsterdam offset, on whole minutes. Walks
  are rounded up, so an option can leave a minute before the `--depart`
  time.
- `maps_url` opens the route in Google Maps (phone or desktop). It's the
  same link for every option, and Maps opens it on "leave now", so the time
  has to be set in Maps. It's useful in a calendar event description.

## Errors

Errors go to stderr as `route: ...`, with exit code 1. Bad flags exit with 2.

- `Google could not find --from '...'`: rephrase the place (add the town)
  or pass `lat,lng`.
- `Google found no public transport route ...`: nothing runs then, e.g. at
  night.
- `Google quota reached` or `local limit reached`: stop. Don't retry, and
  tell the user. The local message says when the next request is allowed.

## Setup

| variable | |
|---|---|
| `ROUTE_GOOGLE_KEY_FILE` | file holding the Google Maps Platform key (Routes API). Required |
| `ROUTE_MAX_REQUESTS` | at most this many Google requests (default 600) ... |
| `ROUTE_LIMIT_DAYS` | ... per this many days (default 7) |

The limit is enforced locally because the Cloud project can't set a daily
quota. Only the times of past requests are kept, in
`$XDG_STATE_HOME/route/requests.json` (default `~/.local/state/route/`),
never their results.

Packaged as a Nix flake: `packages.default`, `overlays.default`
(`pkgs.route-cli`) and `homeManagerModules.default`, which wraps the binary
with those variables:

```nix
programs.route = {
  enable = true;
  keyFile = "/run/secrets/routes-api-key";
  limit = { requests = 600; days = 7; };
};
```
