import datetime as dt

import pytest

from route.errors import RouteError
from route.times import TZ, parse_moment, rfc3339

NOW = dt.date(2026, 11, 12)


def test_winter_time_is_plus_one():
    assert rfc3339(parse_moment("2026-11-14 15:35", now=NOW)) == "2026-11-14T15:35:00+01:00"


def test_summer_time_is_plus_two():
    assert rfc3339(parse_moment("2027-07-01 09:05", now=NOW)) == "2027-07-01T09:05:00+02:00"


def test_dst_change_day_uses_the_offset_after_the_change():
    assert rfc3339(parse_moment("2027-03-28 12:00", now=NOW)) == "2027-03-28T12:00:00+02:00"


@pytest.mark.parametrize("text", ["2026-11-14T15:35", "2026-11-14@15:35", " 2026-11-14 15:35 "])
def test_separators(text):
    assert parse_moment(text, now=NOW) == dt.datetime(2026, 11, 14, 15, 35, tzinfo=TZ)


@pytest.mark.parametrize(("text", "day"), [
    ("today 18:00", dt.date(2026, 11, 12)),
    ("vandaag 18:00", dt.date(2026, 11, 12)),
    ("tomorrow 18:00", dt.date(2026, 11, 13)),
    ("morgen 18:00", dt.date(2026, 11, 13)),
    ("Tomorrow 18:00", dt.date(2026, 11, 13)),
    ("+2 18:00", dt.date(2026, 11, 14)),
    ("14 18:00", dt.date(2026, 11, 14)),
    ("12 18:00", dt.date(2026, 11, 12)),
    ("3 18:00", dt.date(2026, 12, 3)),
    ("11-14 18:00", dt.date(2026, 11, 14)),
    ("01-05 18:00", dt.date(2027, 1, 5)),
])
def test_short_dates(text, day):
    assert parse_moment(text, now=NOW).date() == day


def test_short_day_rolls_over_the_year():
    assert parse_moment("3 10:00", now=dt.date(2026, 12, 20)).date() == dt.date(2027, 1, 3)


@pytest.mark.parametrize("text", ["2026-11-14", "15:35", "2026-11-14 25:00", "2026-13-01 10:00",
                                  "someday 10:00", ""])
def test_rejects(text):
    with pytest.raises(RouteError, match="bad time"):
        parse_moment(text, now=NOW)
