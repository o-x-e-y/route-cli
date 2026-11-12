import os
from pathlib import Path

from .errors import RouteError

DEFAULT_GOOGLE_KEY_FILE = "/run/secrets/google-maps-api-key"


def google_key_file() -> Path:
    return Path(os.environ.get("ROUTE_GOOGLE_KEY_FILE") or DEFAULT_GOOGLE_KEY_FILE)


def google_key() -> str:
    path = google_key_file()
    try:
        key = path.read_text().strip()
    except FileNotFoundError:
        raise RouteError(f"no Google Maps key at {path}: put it there or point "
                         "$ROUTE_GOOGLE_KEY_FILE at the file holding it") from None
    except OSError as error:
        raise RouteError(f"cannot read the Google Maps key at {path}: {error.strerror}") from None
    if not key:
        raise RouteError(f"the Google Maps key file {path} is empty")
    return key
