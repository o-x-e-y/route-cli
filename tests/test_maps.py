from urllib.parse import parse_qs, urlsplit

from route.maps import maps_url


def query(url):
    parts = urlsplit(url)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "www.google.com", "/maps/dir/")
    return {k: v[0] for k, v in parse_qs(parts.query).items()}


def test_text_places():
    url = maps_url("Pathé Eindhoven", "Pathé Tilburg Stappegoor")
    assert url == ("https://www.google.com/maps/dir/?api=1&origin=Path%C3%A9+Eindhoven"
                   "&destination=Path%C3%A9+Tilburg+Stappegoor&travelmode=transit")


def test_lat_lng_is_normalised():
    assert query(maps_url(" 51.4416 , 5.4697", "Helmond"))["origin"] == "51.4416,5.4697"


def test_place_ids():
    q = query(maps_url("Helmond", "Pathé Tilburg Stappegoor",
                       destination_place_id="ChIJg2kuiFC-xkcR9d4ABWTtpnk"))
    assert q == {"api": "1", "origin": "Helmond", "destination": "Pathé Tilburg Stappegoor",
                 "travelmode": "transit", "destination_place_id": "ChIJg2kuiFC-xkcR9d4ABWTtpnk"}
