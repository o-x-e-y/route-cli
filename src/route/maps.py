from urllib.parse import urlencode

from .places import latlng


def _param(text: str) -> str:
    point = latlng(text)
    return f"{point[0]},{point[1]}" if point else text.strip()


def maps_url(origin: str, destination: str, *, origin_place_id: str | None = None,
             destination_place_id: str | None = None) -> str:
    """A documented Maps URL (no key, not billed). It has no time parameter, so
    it opens on "leave now"."""
    params = {"api": "1", "origin": _param(origin), "destination": _param(destination),
              "travelmode": "transit"}
    if origin_place_id:
        params["origin_place_id"] = origin_place_id
    if destination_place_id:
        params["destination_place_id"] = destination_place_id
    return "https://www.google.com/maps/dir/?" + urlencode(params)
