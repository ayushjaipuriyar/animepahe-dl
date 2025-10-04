"""
Configuration constants for the AnimePahe downloader.

This module defines static configuration values, such as API endpoints,
file paths, and downloader settings.

It supports dynamic loading of URL settings from the user's config file.
"""

import os
import secrets
from platformdirs import user_config_dir, user_videos_dir
from typing import Dict, Any

# --- File and Directory Paths ---

APP_NAME = "anime_downloader"
APP_AUTHOR = "Ayush Jaipuriyar"

# The base directory for application data (config, cache, etc.)
BASE_DATA_DIR = user_config_dir(APP_NAME, APP_AUTHOR)
BASE_DOWNLOAD_DIR = user_videos_dir()
# Path to the file containing the user's personal list of anime.
MY_ANIME_LIST_FILE = os.path.join(BASE_DATA_DIR, "myanimelist.txt")

# Path to the file that caches the full list of anime from AnimePahe.
ANIME_LIST_CACHE_FILE = os.path.join(BASE_DATA_DIR, "animelist.txt")

# --- Runtime Configuration ---

# The base URL of the AnimePahe website (can be overridden by user config).
BASE_URL = "https://animepahe.com"


def load_config_from_dict(config_data: Dict[str, Any]):
    """
    Loads dynamic configuration values from a dictionary.
    This should be called at application startup.
    """
    global _runtime_config
    _runtime_config = config_data


# --- API Endpoints & Dynamic Attributes ---

def __getattr__(name: str) -> Any:
    """
    Provides module-level dynamic attributes.

    This allows API endpoints to be constructed dynamically based on the
    `base_url` loaded from the user's configuration.
    """
    if name == "BASE_URL":
        return _runtime_config.get("base_url", _FALLBACK_BASE_URL)

    if name == "API_URL":
        return f"{__getattr__('BASE_URL')}/api"

    if name == "SEARCH_URL":
        return f"{__getattr__('API_URL')}?m=search"

    if name == "RELEASE_URL":
        return f"{__getattr__('API_URL')}?m=release"

    if name == "PLAY_URL":
        return f"{__getattr__('BASE_URL')}/play"

    if name == "AIRING_URL":
        return f"{__getattr__('API_URL')}?m=airing"

    if name == "HTTP_HEADERS":
        return {
            "Referer": __getattr__('BASE_URL'),
            "Cookie": f"__ddg2_={secrets.token_hex(8)}",
        }

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


# --- Downloader Settings ---

# Maximum number of times to retry a failed network request.
MAX_RETRIES = 3

# Factor by which to increase the delay between retries (exponential backoff).
BACKOFF_FACTOR = 2

# Default HTTP headers to use for all requests to AnimePahe.
# A random cookie is generated to mimic a unique user session.
HTTP_HEADERS = {"Referer": BASE_URL, "Cookie": f"__ddg2_={secrets.token_hex(8)}"}


def set_base_url(new_base: str):
    """Update all derived endpoint constants and headers after changing base_url.

    Args:
            new_base: New root URL (scheme + host) e.g. https://example.com
    """
    global BASE_URL, API_URL, SEARCH_URL, RELEASE_URL, PLAY_URL, AIRING_URL, HTTP_HEADERS
    if not new_base or not new_base.startswith("http"):
        return
    # Normalize (remove trailing slash)
    BASE_URL = new_base.rstrip("/")
    API_URL = f"{BASE_URL}/api"
    SEARCH_URL = f"{API_URL}?m=search"
    RELEASE_URL = f"{API_URL}?m=release"
    PLAY_URL = f"{BASE_URL}/play"
    AIRING_URL = f"{API_URL}?m=airing"
    HTTP_HEADERS = {"Referer": BASE_URL, "Cookie": f"__ddg2_={secrets.token_hex(8)}"}


# --- Update Checker ---

# Time in minutes to wait between checking for new episodes.
UPDATE_CHECK_INTERVAL_MINUTES = 30