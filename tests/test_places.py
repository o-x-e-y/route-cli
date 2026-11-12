import pytest

from route.errors import RouteError
from route.places import waypoint


def test_free_text_is_an_address():
    assert waypoint(" Pathé Tilburg Stappegoor ") == {"address": "Pathé Tilburg Stappegoor"}


@pytest.mark.parametrize("text", ["51.4416,5.4697", "51.4416, 5.4697", " 51.4416 ,5.4697 "])
def test_lat_lng(text):
    assert waypoint(text) == {"location": {"latLng": {"latitude": 51.4416, "longitude": 5.4697}}}


def test_negative_coordinates():
    assert waypoint("-33.9,-70.1")["location"]["latLng"] == {"latitude": -33.9, "longitude": -70.1}


def test_address_with_a_comma_stays_an_address():
    assert waypoint("Stationsplein 1, Helmond") == {"address": "Stationsplein 1, Helmond"}


def test_out_of_range():
    with pytest.raises(RouteError, match="valid lat,lng"):
        waypoint("91,5")


def test_empty():
    with pytest.raises(RouteError):
        waypoint("  ")
