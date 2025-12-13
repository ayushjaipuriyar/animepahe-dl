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
import ssl
from urllib3.exceptions import InsecureRequestWarning
import warnings
from bs4 import BeautifulSoup

from ..utils import constants, logger
from ..models import Anime, Episode


class AnimePaheAPI:
    """
    A class to interact with the AnimePahe website and its API.
    Provides methods for searching anime, fetching episodes,
    getting stream URLs, and managing the local cache.
    """

    def __init__(self, verify_ssl: bool = True):  # verify_ssl kept for compatibility
        """Initializes the API with an HTTP client (forced insecure)."""
        self.verify_ssl = False  # Force insecure
        self._insecure_fallback_used = True
        
        # Generate session cookie like the bash script
        self.session_cookie = self._generate_session_cookie()
        
        self.http = self._build_pool(False)
        # Suppress urllib3 insecure request warnings since user explicitly forced insecure mode
        warnings.simplefilter("ignore", InsecureRequestWarning)

    def _generate_session_cookie(self) -> str:
        """Generate a session cookie like the bash script does."""
        import random
        import string
        # Generate random 16-character string like the bash script
        chars = string.ascii_letters + string.digits
        random_str = ''.join(random.choice(chars) for _ in range(16))
        return f"__ddg2_={random_str}"

    def _build_pool(self, verify: bool):
        # Add cookie to headers
        headers = constants.HTTP_HEADERS.copy()
        headers["Cookie"] = self.session_cookie
        
        if verify:
            return urllib3.PoolManager(
                10, headers=headers, cert_reqs="CERT_REQUIRED"
            )
        else:
            return urllib3.PoolManager(
                10,
                headers=headers,
                cert_reqs="CERT_NONE",
                assert_hostname=False,
            )

    # Return type annotated as Any to accommodate urllib3's BaseHTTPResponse hierarchy without strict mismatch
    def _request(self, url: str) -> Optional[Any]:
        """
        Makes a GET request with retries and exponential backoff.

        Args:
            url (str): The URL to request.

        Returns:
            Optional[Any]: Response object or None.
        """
        # Verbose logging for debugging
        import logging
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logger.debug(f"Making request to: {url}")
        
        for attempt in range(constants.MAX_RETRIES):
            try:
                response = self.http.request(
                    "GET", url, preload_content=False, timeout=60
                )
                if response.status == 200:
                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                        logger.debug(f"Request successful: {url} (status: {response.status})")
                    return response
                else:
                    logger.warning(f"Received status code {response.status} for {url}.")
                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                        logger.debug(f"Response headers: {dict(response.headers)}")
            except urllib3.exceptions.SSLError as e:
                # Certificate verification failure handling / optional insecure fallback
                msg = str(e)
                if "CERTIFICATE_VERIFY_FAILED" in msg and self.verify_ssl:
                    logger.warning(
                        "SSL certificate verification failed. You can retry with --insecure (CLI) or set 'allow_insecure_ssl': true in config.json (NOT RECOMMENDED)."
                    )
                    # One-time automatic fallback if user already opted in via config
                    try:
                        from . import config_manager

                        cfg = config_manager.load_config()
                        if (
                            cfg.get("allow_insecure_ssl")
                            and not self._insecure_fallback_used
                        ):
                            logger.warning(
                                "Attempting insecure (certificate verification disabled) retry. Traffic may be intercepted."
                            )
                            self.http = self._build_pool(False)
                            self._insecure_fallback_used = True
                            # Do not count this attempt; retry immediately
                            continue
                    except Exception:
                        pass
                logger.warning(f"A network error occurred: {e}")
            except (
                urllib3.exceptions.MaxRetryError,
                urllib3.exceptions.HTTPError,
                urllib3.exceptions.TimeoutError,
                urllib3.exceptions.InvalidHeader,
                urllib3.exceptions.ProxyError,
            ) as e:
                logger.warning(f"A network error occurred: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                return None  # Don't retry on unexpected errors

            if attempt < constants.MAX_RETRIES - 1:
                sleep_time = constants.BACKOFF_FACTOR ** (attempt + 1)
                logger.info(
                    f"Retrying in {sleep_time} seconds... ({attempt + 1}/{constants.MAX_RETRIES})"
                )
                time.sleep(sleep_time)
            else:
                logger.error(
                    f"Failed to download {url} after {constants.MAX_RETRIES} attempts."
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
                with open(constants.ANIME_LIST_CACHE_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        slug, title = line.strip().split("::::", 1)
                        search_results.append({"session": slug, "title": title})
                return search_results
            except FileNotFoundError:
                logger.warning(
                    "Anime list cache not found. Please run with --update-cache first."
                )
                return []

        response = self._request(f"{constants.SEARCH_URL}&q={query}")
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
        api_url = f"{constants.RELEASE_URL}&id={anime_slug}&sort=episode_asc&page=1"
        response = self._request(api_url)
        if not response:
            return []

        data = json.loads(response.data)
        last_page = data.get("last_page", 1)
        all_episodes = data.get("data", [])

        for page_num in range(2, last_page + 1):
            page_url = (
                f"{constants.RELEASE_URL}&id={anime_slug}&sort=episode_asc&page={page_num}"
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
        play_url = f"{constants.PLAY_URL}/{anime_slug}/{episode_session}"
        response = self._request(play_url)
        if not response:
            logger.error("Failed to get episode page.")
            return None

        soup = BeautifulSoup(response.data, "html.parser")
        buttons = soup.find_all("button", attrs={"data-src": True, "data-av1": "0"})

        # Extract only the primitive values we need into plain Python dicts
        streams: List[Dict[str, Any]] = []
        for b in buttons:
            streams.append(
                {
                    "quality": b.get("data-resolution") or "0",
                    "audio": b.get("data-audio") or None,
                    "url": b.get("data-src") or None,
                }
            )

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
            q_raw = s.get("quality")
            try:
                s["quality_val"] = int(q_raw) if q_raw is not None else 0
            except (ValueError, TypeError):
                s["quality_val"] = 0

        # Sort streams by quality descending
        streams.sort(key=lambda s: int(s.get("quality_val", 0)), reverse=True)

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
                    if int(stream.get("quality_val", 0)) <= target_quality:
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
            return selected_stream.get("url")  # type: ignore[return-value]
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
        # Find all script tags and inspect their string content
        scripts = soup.find_all("script")
        for script in scripts:
            script_text = script.string or ""
            if "eval(" in script_text:
                modified_script = (
                    script_text.replace("document", "process")
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
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                    logger.error(f"Could not evaluate script to get playlist link: {e}")
                    return None
        logger.error("Could not find or evaluate the script to get the playlist link.")
        return None

    def download_anime_list_cache(self) -> int:
        """Download and cache the full list of anime.

        Returns:
            int: Number of entries written to the cache file.
                 -1 indicates a download/network failure (existing cache left untouched).
                 0 indicates the request succeeded but no entries were parsed (likely site layout change or empty response).
        """
        logger.info("Updating anime list cache...")
        response = self._request(f"{constants.get_base_url()}/anime/")
        if not response:
            logger.warning(
                "Failed to download anime list. Using existing cache if available."
            )
            return -1

        soup = BeautifulSoup(response.data, "html.parser")
        div_container = soup.find_all("div", {"class": "tab-content"})
        count = 0
        try:
            with open(constants.ANIME_LIST_CACHE_FILE, "w", encoding="utf-8") as f:
                for tag in div_container:
                    for a_tag in tag.find_all("a"):
                        href = a_tag.get("href") or ""
                        if not href:
                            continue
                        href_str = str(href)
                        uuid = href_str.split("/")[-1]
                        name = a_tag.text.strip()
                        # Skip obviously empty lines
                        if not uuid or not name:
                            continue
                        f.write(f"{uuid}::::{name}\n")
                        count += 1
        except OSError as e:
            logger.error(f"Failed writing cache file: {e}")
            return -1

        logger.debug(f"Parsed {count} entries from anime list page.")
        return count

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """
        Checks for newly aired episodes on AnimePahe.

        Returns:
            List[Dict[str, Any]]: New episode data.
        """
        response = self._request(f"{constants.AIRING_URL}&page=1")
        if not response:
            logger.error("Could not fetch airing anime list.")
            return []
        return json.loads(response.data).get("data", [])
