"""
This module handles all interactions with the AnimePahe website and its API.
"""

import json
import os
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

import urllib3
from bs4 import BeautifulSoup

from . import config
from .models import Anime, Episode
from .logger import logger


class AnimePaheAPI:
    """
    A class to interact with the AnimePahe website and its API.
    Provides methods for searching anime, fetching episodes,
    getting stream URLs, and managing the local cache.
    """

    def __init__(self):
        """Initializes the API with an HTTP client."""
        self.http = urllib3.PoolManager(10, headers=config.HTTP_HEADERS)

    def _request(self, url: str) -> Optional[urllib3.HTTPResponse]:
        """
        Makes a GET request with retries and exponential backoff.

        Args:
            url (str): The URL to request.

        Returns:
            Optional[urllib3.HTTPResponse]: Response object or None.
        """
        for attempt in range(config.MAX_RETRIES):
            try:
                response = self.http.request(
                    "GET", url, preload_content=False, timeout=60
                )
                if response.status == 200:
                    return response
                else:
                    logger.warning(
                        f"Received status code {response.status} for {url}."
                    )
            except (
                urllib3.exceptions.MaxRetryError,
                urllib3.exceptions.HTTPError,
                urllib3.exceptions.TimeoutError,
                urllib3.exceptions.InvalidHeader,
                urllib3.exceptions.ProxyError,
                urllib3.exceptions.SSLError,
            ) as e:
                logger.warning(f"A network error occurred: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None  # Don't retry on unexpected errors

            if attempt < config.MAX_RETRIES - 1:
                sleep_time = config.BACKOFF_FACTOR ** (attempt + 1)
                logger.info(
                    f"Retrying in {sleep_time} seconds... ({attempt + 1}/{config.MAX_RETRIES})"
                )
                time.sleep(sleep_time)
            else:
                logger.error(
                    f"Failed to download {url} after {config.MAX_RETRIES} attempts."
                )
                return None

        return None

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Searches for anime on AnimePahe.

        Args:
            query (str): The search query.

        Returns:
            List[Dict[str, str]]: List of search result dicts.
        """
        search_results = []
        if not query:
            try:
                with open(config.ANIME_LIST_CACHE_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        slug, title = line.strip().split("::::", 1)
                        search_results.append({"session": slug, "title": title})
                return search_results
            except FileNotFoundError:
                logger.warning(
                    "Anime list cache not found. Please run with --update-cache first."
                )
                return []

        response = self._request(f"{config.SEARCH_URL}&q={query}")
        if response:
            data = json.loads(response.data)
            return data.get("data", [])
        return []

    def fetch_episode_data(
        self, anime_name: str, anime_slug: str
    ) -> List[Dict[str, Any]]:
        """
        Fetches the full list of episodes for a given anime.

        Args:
            anime_name (str): The name of the anime (for logging).
            anime_slug (str): The anime's session ID.

        Returns:
            List[Dict[str, Any]]: Episode data.
        """
        logger.info(f"Fetching episode list for '{anime_name}'...")
        api_url = f"{config.RELEASE_URL}&id={anime_slug}&sort=episode_asc&page=1"
        response = self._request(api_url)
        if not response:
            return []

        data = json.loads(response.data)
        last_page = data.get("last_page", 1)
        all_episodes = data.get("data", [])

        for page_num in range(2, last_page + 1):
            page_url = (
                f"{config.RELEASE_URL}&id={anime_slug}&sort=episode_asc&page={page_num}"
            )
            response = self._request(page_url)
            if response:
                page_data = json.loads(response.data).get("data", [])
                all_episodes.extend(page_data)

        return all_episodes

    def get_stream_url(
        self, anime_slug: str, episode_session: str, quality: str, audio: str
    ) -> Optional[str]:
        """
        Gets the final stream URL for a specific episode with flexible quality and audio selection.

        Args:
            anime_slug (str): Anime session ID.
            episode_session (str): Episode session ID.
            quality (str): Desired quality (e.g., '720', '1080', 'best').
            audio (str): Desired audio language (e.g., 'jpn', 'eng').

        Returns:
            Optional[str]: Direct stream URL or None.
        """
        play_url = f"{config.PLAY_URL}/{anime_slug}/{episode_session}"
        response = self._request(play_url)
        if not response:
            logger.error("Failed to get episode page.")
            return None

        soup = BeautifulSoup(response.data, "html.parser")
        buttons = soup.find_all("button", attrs={"data-src": True, "data-av1": "0"})

        streams = [
            {
                "quality": b.get("data-resolution"),
                "audio": b.get("data-audio"),
                "url": b.get("data-src"),
            }
            for b in buttons
        ]

        if not streams:
            logger.warning("No streams found on the page.")
            return None

        # Log available streams for debugging
        available_streams_str = ", ".join(
            [f"{s['quality']}p ({s['audio']})" for s in streams if s.get("quality")]
        )
        logger.info(f"Available streams: {available_streams_str}")

        # Convert quality to integer for sorting, handle non-numeric qualities
        for s in streams:
            try:
                s["quality_val"] = int(s["quality"])
            except (ValueError, TypeError):
                s["quality_val"] = 0  # Assign 0 if quality is not a number

        # Sort streams by quality descending
        streams.sort(key=lambda s: s["quality_val"], reverse=True)

        # --- Audio Selection ---
        audio_streams = [s for s in streams if s.get("audio") == audio]
        if not audio_streams:
            logger.warning(
                f"Audio '{audio}' not found. Selecting from available audio languages."
            )
            audio_streams = streams  # Fallback to all streams

        # --- Quality Selection ---
        selected_stream = None
        if quality == "best":
            if audio_streams:
                selected_stream = audio_streams[0]
        else:
            try:
                target_quality = int(quality)
                # Find best match: exact or next best available
                for stream in audio_streams:
                    if stream["quality_val"] <= target_quality:
                        selected_stream = stream
                        break
                # If no stream is <= target, pick the best available (first in sorted list)
                if not selected_stream and audio_streams:
                    selected_stream = audio_streams[0]
                    logger.warning(
                        f"Quality '{quality}p' not found. "
                        f"Selected next best available: {selected_stream['quality']}p."
                    )
            except ValueError:
                logger.error(
                    f"Invalid quality specified: '{quality}'. Please use 'best' or a number like '720'."
                )
                return None

        if selected_stream:
            logger.success(
                f"Selected stream: {selected_stream['quality']}p ({selected_stream['audio']})"
            )
            return selected_stream["url"]
        else:
            logger.warning("Could not find any matching stream after filtering.")
            return None

    def get_playlist_url(self, stream_url: str) -> Optional[str]:
        """
        Extracts the m3u8 playlist URL from the stream page.

        Args:
            stream_url (str): URL of the stream page.

        Returns:
            Optional[str]: m3u8 playlist URL or None.
        """
        response = self._request(stream_url)
        if not response:
            logger.error("Failed to get playlist page.")
            return None

        soup = BeautifulSoup(response.data, "html.parser")
        scripts = soup.find_all("script", string=True)
        for script in scripts:
            if "eval(" in script.string:
                modified_script = (
                    script.string.replace("document", "process")
                    .replace("querySelector", "exit")
                    .replace("eval(", "console.log(")
                )
                try:
                    p = subprocess.run(
                        ["node", "-e", modified_script],
                        stdout=subprocess.PIPE,
                        text=True,
                        timeout=5,
                    )
                    match = re.search(r"const source='(.*?).m3u8", p.stdout)
                    if match:
                        return match.group(1) + ".m3u8"
                    else:
                        logger.error("No m3u8 source found in script output.")
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                    logger.error(f"Could not evaluate script to get playlist link: {e}")
                    return None
        logger.error("Could not find or evaluate the script to get the playlist link.")
        return None

    def download_anime_list_cache(self):
        """
        Downloads and caches the full list of anime from AnimePahe.
        """
        logger.info("Updating anime list cache...")
        response = self._request(f"{config.BASE_URL}/anime/")
        if not response:
            logger.warning(
                "Failed to download anime list. Using existing cache if available."
            )
            return

        soup = BeautifulSoup(response.data, "html.parser")
        div_container = soup.find_all("div", {"class": "tab-content"})
        with open(config.ANIME_LIST_CACHE_FILE, "w", encoding="utf-8") as f:
            for tag in div_container:
                for a_tag in tag.find_all("a"):
                    uuid = a_tag.attrs["href"].split("/")[-1]
                    name = a_tag.text.strip()
                    f.write(f"{uuid}::::{name}\n")
        logger.info("Anime list cache updated.")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Checks for newly aired episodes on AnimePahe.

        Returns:
            List[Dict[str, Any]]: New episode data.
        """
        response = self._request(f"{config.AIRING_URL}&page=1")
        if not response:
            logger.error("Could not fetch airing anime list.")
            return []
        return json.loads(response.data).get("data", [])
