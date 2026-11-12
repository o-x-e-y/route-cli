import os
from pathlib import Path

from .errors import RouteError

DEFAULT_MAX_REQUESTS = 600
DEFAULT_LIMIT_DAYS = 7


def google_key() -> str:
    name = os.environ.get("ROUTE_GOOGLE_KEY_FILE")
    if not name:
        raise RouteError("no Google Maps key: set $ROUTE_GOOGLE_KEY_FILE to the file holding it "
                         "(programs.route.keyFile in home-manager)")
    path = Path(name)
    try:
        key = path.read_text().strip()
    except FileNotFoundError:
        raise RouteError(f"no Google Maps key at {path} ($ROUTE_GOOGLE_KEY_FILE)") from None
    except OSError as error:
        raise RouteError(f"cannot read the Google Maps key at {path}: {error.strerror}") from None
    if not key:
        raise RouteError(f"the Google Maps key file {path} is empty")
    return key


def limit() -> tuple[int, int]:
    """At most this many Google requests in this many days."""
    return (_count("ROUTE_MAX_REQUESTS", DEFAULT_MAX_REQUESTS),
            _count("ROUTE_LIMIT_DAYS", DEFAULT_LIMIT_DAYS))


def _count(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit():
        raise RouteError(f"${name} must be a whole number, not {raw!r}")
    return int(raw)


def state_dir() -> Path:
    root = os.environ.get("XDG_STATE_HOME", "").strip()
    return (Path(root) if root else Path.home() / ".local" / "state") / "route"
