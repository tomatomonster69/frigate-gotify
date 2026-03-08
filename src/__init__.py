"""Frigate-Gotify notification bridge."""

from .config import settings
from .frigate_client import FrigateClient, ReviewEvent, Event
from .gotify_client import GotifyClient
from .main import FrigateGotifyBridge

__version__ = "0.1.0"
__all__ = [
    "settings",
    "FrigateClient",
    "ReviewEvent",
    "Event",
    "GotifyClient",
    "FrigateGotifyBridge",
]