
"""
This module provides utility functions for the AnimePahe Downloader.
"""

import urllib3
import json

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string to be used as a valid file or folder name.

    Args:
        name: The string to sanitize.

    Returns:
        The sanitized string.
    """
    name = name.lstrip(".")
    # Remove invalid characters for Windows filenames
    invalid_chars = '<>/\\|:\"*?'
    for char in invalid_chars:
        name = name.replace(char, '')
    return "".join(c for c in name if c.isalnum() or c in " .-_()").rstrip()

def get_airing_anime():
    """
    Fetches the currently airing anime from AnimePahe.

    Returns:
        A dictionary containing the airing anime data, or None if the request fails.
    """
    try:
        http = urllib3.PoolManager(10, headers={"Referer": "https://kwik.cx/", "Accept": "","Connection": "Keep-Alive","Accept-Encoding": "gzip, deflate, br","Accept-Language": "en-US,en;q=0.9","User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36"})
        res = "https://animepahe.ru/api?m=airing&page1"
        r = http.request("GET", res, preload_content=False)
        return json.loads(r.data)
    except (urllib3.exceptions.MaxRetryError, json.JSONDecodeError) as e:
        print(f"Error fetching airing anime: {e}")
        return None
