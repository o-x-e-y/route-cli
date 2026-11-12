# route-cli plan

A small CLI that answers one question for public transport in the
Netherlands: **"from X to Y, departing at / arriving by T, what are the
options?"**

Its main user is an AI agent, not a person reading the output while
travelling. A typical flow:

> "Saturday I'm seeing The Devils at Pathé Tilburg Stappegoor, I work until
> 15:30." The agent looks up the showtime and shift end itself (other tools),
> calls `route` for the trip there and the trip back, decides whether it's
> feasible, picks the fastest option and puts it in the calendar.

So the goal is the overall picture of a trip planned in advance: leave time,
arrival time, duration, transfers, which lines. Platforms and live delays
are nice to have, not needed. The agent does the feasibility check,
calendar events and showtime lookup. The CLI only does routing.

## Before you start

- This folder is not a git repo yet. Run `git init` first and commit as you
  go, so the user can follow the changes.
- The Google Routes details below (request body, field mask, how
  alternatives work for transit) are written from memory, not from a test
  request. Check them against the current docs and adjust step 2 to match.
- Step 1 of "Order of work" needs no API key. The Google key isn't set up
  yet: when you reach step 2 and the key file doesn't exist, stop and tell
  the user, and don't mock the API to get past it.

## Interface

```
route --from "Pathé Eindhoven" --to "Pathé Tilburg Stappegoor" --depart "2026-11-14 15:35" --json
route --from "Pathé Tilburg Stappegoor" --to "Helmond" --arrive "2026-11-14 23:30" --json
```

- `--from` / `--to`: free text (place name, address, station) or `lat,lng`.
- `--depart` or `--arrive`: local time (Europe/Amsterdam).
- `--json`: the main output, for agents. Without it, print a short readable
  summary.
- Return several options (alternatives), not just the fastest. The agent
  chooses.

JSON per option, roughly:

```json
{
  "depart": "2026-11-14T15:41:00+01:00",
  "arrive": "2026-11-14T16:52:00+01:00",
  "duration_min": 71,
  "transfers": 2,
  "legs": [
    {"mode": "walk", "from": "...", "to": "...", "depart": "...", "arrive": "...", "duration_min": 6},
    {"mode": "train", "line": "Intercity", "headsign": "...", "from": "Eindhoven Centraal", "to": "Tilburg", "depart": "...", "arrive": "..."},
    {"mode": "bus", "line": "1", "from": "Tilburg, Centraal Station", "to": "Tilburg, Stappegoor/IJsbaan", "depart": "...", "arrive": "..."}
  ],
  "maps_url": "https://www.google.com/maps/dir/?api=1&..."
}
```

Also print what `--from` and `--to` resolved to (name + coordinates), so a
wrong match is easy to spot.

## Data source: Google Routes API (main)

One door-to-door `TRANSIT` request per query: train, bus, tram and walking
legs together, from any origin to any destination. No stitching logic.

```
POST https://routes.googleapis.com/directions/v2:computeRoutes
X-Goog-Api-Key: ...
X-Goog-FieldMask: routes.duration,routes.legs.steps.travelMode,routes.legs.steps.transitDetails,...
```

- The field mask is **required**. Requests without it fail. Request only the
  fields you use.
- Body: `origin` / `destination` as `{address: "..."}`,
  `{location: {latLng: {...}}}` or `{placeId: ...}`; `travelMode: "TRANSIT"`;
  `departureTime` **or** `arrivalTime` (RFC3339; `arrivalTime` only works for
  transit); `computeAlternativeRoutes: true`; `languageCode: "nl"`.
- Free text in `address` should resolve places like "Pathé Tilburg
  Stappegoor" by itself. Check this. If it's unreliable, use a separate
  lookup (Google Places or NS Places, see below).
- **Not tested yet** (no key so far). Check all of the above against the
  current docs before coding.

### Billing and limits

- Plain `TRANSIT` requests fall under "Compute Routes Essentials": 10,000
  free per month, then $5 per 1,000. Don't use Pro features
  (traffic-aware routing, more than 10 waypoints), which bill under Pro
  (5,000 free).
- The user will set a daily quota (~300/day) in Cloud Console as a
  server-side hard stop. On `429`, exit with a clear "Google quota
  reached" error and **don't retry**.
- No caching or storing of Google results beyond the current run (Google
  ToS).

## Fallback: Transitous (add only if Google turns out to be a problem)

Free and community-run (MOTIS), with no key. Uses Dutch GTFS (OpenOV), so
buses are included. **Verified on 2026-11-12**: Helmond → Stappegoor returned
IC → IC → bus 1 itineraries.

```
GET https://api.transitous.org/api/v5/plan?fromPlace=<lat,lng or stop id>&toPlace=<lat,lng>&time=2026-11-13T17:00:00Z
GET https://api.transitous.org/api/v1/geocode?text=Pathe%20Tilburg%20Stappegoor
```

- `itineraries[]` with `startTime`, `endTime`, `duration` (seconds),
  `transfers`, `legs[]` (`mode` e.g. `REGIONAL_RAIL` / `BUS` / `WALK`,
  `routeShortName`, `from.name`, `to.name`, `startTime`, `endTime`).
  Times are UTC.
- Geocode returns `type` (`STOP` / `PLACE`), `name`, `lat`, `lon`, `id`
  (e.g. `nl-OpenOV_stoparea:18111` = Helmond station).
- Fair use: send a descriptive User-Agent and don't hammer it.

If added, it goes behind the same JSON output so that the agent can't tell
which source answered, apart from a `"source"` field.

## Google Maps link

Every option gets a `maps_url` that opens the route in Google Maps on the
phone or desktop. This uses the documented, free Maps URLs, which need no
API key and aren't billed:

```
https://www.google.com/maps/dir/?api=1&origin=<urlencoded>&destination=<urlencoded>&travelmode=transit
```

- Optional `origin_place_id` / `destination_place_id` if a Google place ID
  is known (more precise than text).
- **Limitation:** Maps URLs have no departure/arrival time parameter, so the
  link opens with "leave now" and the user sets the time in Maps. There
  are undocumented `data=!4m...` parameters that do encode a time. Don't
  use them unless they turn out to be stable.
- The link is the same for every option of a query (Maps picks its own
  route), so returning it once per query is fine.
- The agent can put this link in the calendar event description.

## Later, maybe: NS API

Not part of v1. For planning in advance, Google's timetable is enough. NS
only becomes useful for day-of checks (live delays, platforms, planned
engineering work), if that's ever wanted. Facts already verified, so they
don't need rediscovering:

- Key: `/run/secrets/ns-api-key`, header `Ocp-Apim-Subscription-Key`, base
  `https://gateway.apiportal.ns.nl`, 300 requests / 5 min.
- Works: `GET /reisinformatie-api/api/v3/trips?fromStation=HM&toStation=TB&dateTime=2026-11-13T18:00:00+01:00`
  (station codes only). Legs have `plannedTrack` / `actualTrack`,
  `plannedDateTime` / `actualDateTime`, `product.displayName`, `cancelled`.
- Doesn't work with this key: coordinates
  (`API_KEY_NOT_ALLOWED_TO_PLAN_DOOR_TO_DOOR`) or bus stop codes (bare `400`).
- Places API works with the same key:
  `GET /places-api/v2/places?q=Stappegoor&type=stop,address,poi`. `poi`
  results carry a Google `placeId` (Pathé Tilburg Stappegoor =
  `ChIJg2kuiFC-xkcR9d4ABWTtpnk`), which is usable for Google Routes and
  Maps URLs if Google's own text lookup is unreliable.

## Secrets

| Secret | Location | Header |
|---|---|---|
| Google Maps Platform key | not set up yet, likely `/run/secrets/google-maps-api-key` | `X-Goog-Api-Key` |
| NS key (only if NS is added) | `/run/secrets/ns-api-key` | `Ocp-Apim-Subscription-Key` |

Read keys from files at runtime and make the path configurable (env var).
Never print, log or commit them.

## Implementation constraints

- The user's machine is NixOS. Package it with a `flake.nix` so it can be
  added to their config later. Don't touch `~/nixos` yourself.
- Keep it small (YAGNI). Suggested: Python with the stdlib only (`urllib`,
  `json`, `argparse`, `zoneinfo`). Pick something else only if you have a
  good reason.
- Only add comments where the reason isn't obvious from the code.
- Tests: unit-test the response → JSON conversion, time zone handling and
  Maps URL building against saved responses. Don't hit the APIs in tests.
  Save real responses as fixtures, with no keys in them.
- Use `trash-put` instead of `rm`.
- Include a short `README.md` aimed at agents: what the tool answers, the
  flags, the JSON shape, and that `--arrive` plans backwards from a fixed
  time. Agents will read that, not this plan.

## Order of work

1. Flake + skeleton CLI, argument and time parsing, Maps URL generation
   (needs no key, so it can be done right away).
2. Google Routes `TRANSIT` request + JSON output, once the user has the key
   and quota set up. Test with Eindhoven → Pathé Tilburg Stappegoor on a
   Saturday afternoon, and the trip back late in the evening.
3. Readable text output and `README.md`.
4. Only if needed: Transitous fallback, NS day-of checks.

## Open questions for the user

- Path of the Google key, and confirmation that the Cloud project, billing,
  Routes API and daily quota are set up.
- Whether to add it to `~/nixos` once it works, and whether to turn it into
  a skill so agents find it on their own.
