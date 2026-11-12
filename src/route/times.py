import datetime as dt
import re
from zoneinfo import ZoneInfo

from .errors import RouteError

TZ = ZoneInfo("Europe/Amsterdam")

_MOMENT = re.compile(r"^(?P<date>\S+?)[ T@](?P<time>\d{1,2}:\d{2})$", re.IGNORECASE)

FORMS = "'DATE HH:MM', DATE being YYYY-MM-DD, MM-DD, DD, today, tomorrow or +N"


def today() -> dt.date:
    return dt.datetime.now(TZ).date()


def parse_moment(value: str, *, now: dt.date | None = None) -> dt.datetime:
    """A local moment in Europe/Amsterdam. A short date (MM-DD, DD) is the next
    such date, today included."""
    match = _MOMENT.match(value.strip())
    if not match:
        raise RouteError(f"bad time {value!r}: expected {FORMS}")
    try:
        day = _date(match["date"].lower(), now or today())
        hour, minute = (int(part) for part in match["time"].split(":"))
        return dt.datetime.combine(day, dt.time(hour, minute), tzinfo=TZ)
    except ValueError:
        raise RouteError(f"bad time {value!r}: expected {FORMS}") from None


def _date(value: str, now: dt.date) -> dt.date:
    if value in ("today", "vandaag"):
        return now
    if value in ("tomorrow", "morgen"):
        return now + dt.timedelta(days=1)
    if value.startswith("+") and value[1:].isdigit():
        return now + dt.timedelta(days=int(value[1:]))
    if re.fullmatch(r"\d{1,2}", value):
        date = now.replace(day=int(value))
        if date < now:
            year, month = divmod(now.year * 12 + now.month, 12)
            date = dt.date(year, month + 1, int(value))
        return date
    if m := re.fullmatch(r"(\d{1,2})-(\d{1,2})", value):
        date = dt.date(now.year, int(m[1]), int(m[2]))
        return date if date >= now else date.replace(year=now.year + 1)
    return dt.date.fromisoformat(value)


def rfc3339(moment: dt.datetime) -> str:
    return moment.isoformat(timespec="seconds")
