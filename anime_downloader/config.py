"""
Configuration constants for the AnimePahe downloader.

This module defines static configuration values, such as API endpoints,
file paths, and downloader settings.
"""

import os
import secrets
from platformdirs import user_config_dir, user_videos_dir

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


# --- API Endpoints ---

# The base URL of the AnimePahe website.
BASE_URL = "https://animepahe.si"

# The base URL for the AnimePahe API.
API_URL = f"{BASE_URL}/api"

# API endpoint for searching for anime.
SEARCH_URL = f"{API_URL}?m=search"

# API endpoint for fetching episode release information.
RELEASE_URL = f"{API_URL}?m=release"

# Base URL for the episode playback page.
PLAY_URL = f"{BASE_URL}/play"

# API endpoint for fetching currently airing anime.
AIRING_URL = f"{API_URL}?m=airing"


# --- Downloader Settings ---

# Maximum number of times to retry a failed network request.
MAX_RETRIES = 3

# Factor by which to increase the delay between retries (exponential backoff).
BACKOFF_FACTOR = 2

# Default HTTP headers to use for all requests to AnimePahe.
# A random cookie is generated to mimic a unique user session.
HTTP_HEADERS = {"Referer": BASE_URL, "Cookie": f"__ddg2_={secrets.token_hex(8)}"}

# --- Update Checker ---

# Time in minutes to wait between checking for new episodes.
UPDATE_CHECK_INTERVAL_MINUTES = 30
