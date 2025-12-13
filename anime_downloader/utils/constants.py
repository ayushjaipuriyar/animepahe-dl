"""
Constants and configuration values for the AnimePahe Downloader.

This module contains all the constants that were previously in the config module,
providing backward compatibility while the codebase transitions to the new OOP structure.
"""

import os
from pathlib import Path

# Base URLs and API endpoints
BASE_URL = "https://animepahe.si"
SEARCH_URL = f"{BASE_URL}/api?m=search"
RELEASE_URL = f"{BASE_URL}/api?m=release"
PLAY_URL = f"{BASE_URL}/play"
AIRING_URL = f"{BASE_URL}/api?m=airing"

# HTTP configuration
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://animepahe.si",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

# Network configuration
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
TIMEOUT = 60

# Directory paths
BASE_DATA_DIR = os.path.join(Path.home(), ".config", "animepahe-dl")
BASE_DOWNLOAD_DIR = os.path.join(Path.home(), "Videos")

# File paths
ANIME_LIST_CACHE_FILE = os.path.join(BASE_DATA_DIR, "anime_list.cache")
MY_ANIME_LIST_FILE = os.path.join(BASE_DATA_DIR, "my_anime_list.txt")

# Update configuration
UPDATE_CHECK_INTERVAL_MINUTES = 60

# Global base URL override functionality
_current_base_url = BASE_URL

def set_base_url(new_base_url: str):
    """
    Updates the base URL and all related API endpoints.
    
    Args:
        new_base_url: The new base URL to use.
    """
    global _current_base_url, SEARCH_URL, RELEASE_URL, PLAY_URL, AIRING_URL
    _current_base_url = new_base_url.rstrip('/')
    SEARCH_URL = f"{_current_base_url}/api?m=search"
    RELEASE_URL = f"{_current_base_url}/api?m=release"
    PLAY_URL = f"{_current_base_url}/play"
    AIRING_URL = f"{_current_base_url}/api?m=airing"

def get_base_url() -> str:
    """Get the current base URL."""
    return _current_base_url

# Ensure data directory exists
os.makedirs(BASE_DATA_DIR, exist_ok=True)