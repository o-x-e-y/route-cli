"""A local cap on Google requests, since the Cloud project can't set a daily
quota. Only the times of past requests are kept, never their results."""

import datetime as dt
import fcntl
import json
from pathlib import Path

from .errors import RouteError
from .times import TZ


def spend(path: Path, max_requests: int, days: int, now: dt.datetime) -> None:
    """Count one request, or refuse when the window is already full."""
    path.parent.mkdir(parents=True, exist_ok=True)
    window = dt.timedelta(days=days)
    with path.open("a+") as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        file.seek(0)
        try:
            stamps = [dt.datetime.fromisoformat(s) for s in json.loads(file.read() or "[]")]
        except (ValueError, TypeError):
            raise RouteError(f"{path} is not a list of request times; fix or remove it") from None
        stamps = sorted(s for s in stamps if s > now - window)
        if len(stamps) >= max_requests:
            free = (stamps[-max_requests] + window).astimezone(TZ)
            raise RouteError(f"local limit reached: {max_requests} Google requests per {days} "
                             f"days; the next one is allowed from {free:%Y-%m-%d %H:%M}")
        stamps.append(now)
        file.seek(0)
        file.truncate()
        json.dump([s.isoformat(timespec="seconds") for s in stamps], file)
