"""
This module handles all interactions with the AnimePahe website and its API.
"""

import json
import logging
import os
import re
import ssl
import subprocess
import time
import warnings
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from anime_downloader.utils import config_manager

from ..models import Anime, Episode
from ..utils import constants, logger


class _CffiResponseWrapper:
    """Thin wrapper around curl_cffi Response to match urllib3 response API.

    Provides ``.status``, ``.headers``, ``.data``, and ``.close()`` so the rest
    of the codebase that was written against urllib3 keeps working unchanged.
    """

    def __init__(self, response: cffi_requests.Response) -> None:
        self._response = response
        self.status = response.status_code
        self.headers = response.headers

    @property
    def data(self) -> bytes:
        return self._response.content

    def close(self) -> None:
        self._response.close()


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
        self._browser_challenge_active = False  # Guard against infinite browser loops

        self.config = config_manager.load_config()

        cookie_file = self.config.get("cookie_file", "").strip()
        cf_clearance = self.config.get("cf_clearance", "").strip()

        self.session_cookie = ""
        if cookie_file and os.path.isfile(cookie_file):
            self.session_cookie = self._load_cookies_from_file(cookie_file)

        if not self.session_cookie and cf_clearance:
            self.session_cookie = f"cf_clearance={cf_clearance}"

        if not self.session_cookie:
            self.session_cookie = self._generate_session_cookie()

        self.http = self._build_session()

        # Best-effort startup probe to refresh cookies and follow the current host.
        self.startup_probe()

    def _generate_session_cookie(self) -> str:
        """Generate a session cookie like the bash script does."""
        import random
        import string

        # Generate random 16-character string like the bash script
        chars = string.ascii_letters + string.digits
        random_str = "".join(random.choice(chars) for _ in range(16))
        return f"__ddg2_={random_str}"

    def _load_cookies_from_file(self, file_path: str) -> str:
        """Loads cookies from a Netscape format or JSON file and returns a Cookie header string."""
        cookie_str = ""
        if file_path.endswith('.json'):
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list):
                        cookie_pairs = [f"{c['name']}={c['value']}" for c in cookies if 'name' in c and 'value' in c]
                        cookie_str = "; ".join(cookie_pairs)
                    elif isinstance(cookies, dict):
                        cookie_pairs = [f"{k}={v}" for k, v in cookies.items()]
                        cookie_str = "; ".join(cookie_pairs)
            except Exception as e:
                logger.error(f"Error reading JSON cookie file: {e}")
        else:
            import http.cookiejar
            cj = http.cookiejar.MozillaCookieJar(file_path)
            try:
                cj.load(ignore_discard=True, ignore_expires=True)
                cookie_pairs = [f"{cookie.name}={cookie.value}" for cookie in cj]
                cookie_str = "; ".join(cookie_pairs)
            except Exception as e:
                # Fallback: just read raw cookie string if it's not a valid Mozilla format
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content.startswith("# Netscape"):
                            cookie_str = content
                except Exception as inner_e:
                    logger.error(f"Error reading cookie file: {e}")
        return cookie_str

    def _build_session(self) -> cffi_requests.Session:
        """Build a curl_cffi Session that impersonates Chrome's TLS fingerprint."""
        headers = constants.HTTP_HEADERS.copy()

        user_agent = self.config.get("user_agent", "")
        if user_agent:
            headers["User-Agent"] = user_agent

        headers["Cookie"] = self.session_cookie

        session = cffi_requests.Session(impersonate="chrome")
        session.headers.update(headers)
        session.verify = False
        return session

    def _capture_set_cookie_headers(self, response: Any) -> None:
        """Capture cookies from a response and rebuild the session if they changed."""
        try:
            set_cookie_hdr = response.headers.get("set-cookie") or response.headers.get(
                "Set-Cookie"
            )
            if not set_cookie_hdr:
                return

            sc = SimpleCookie()
            sc.load(set_cookie_hdr)
            cookie_pairs = [f"{k}={v.value}" for k, v in sc.items()]
            if not cookie_pairs:
                return

            new_cookie = "; ".join(cookie_pairs)
            if new_cookie != self.session_cookie:
                self.session_cookie = new_cookie
                self.http = self._build_session()
                logger.info("Captured cookies from response and rebuilt the request session")
        except Exception:
            pass
    def _fetch_clearance_via_browser(self) -> bool:
        """Launches a visible browser to let the user pass Cloudflare.

        Protected by ``_browser_challenge_active`` to prevent infinite loops.
        """
        if self._browser_challenge_active:
            logger.warning("Browser challenge already in progress, skipping to avoid loop.")
            return False

        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            import sys
            logger.error(f"Playwright import failed: {e}. Python executable: {sys.executable}. sys.path: {sys.path}")
            return False

        self._browser_challenge_active = True
        logger.info("Opening local browser to solve Cloudflare challenge...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"],
                )
                context = browser.new_context()
                context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = context.new_page()

                # Navigate to the base URL
                page.goto(constants.get_base_url())
                logger.info("Please solve the Cloudflare challenge in the browser window.")
                logger.info("Waiting for the cf_clearance cookie to be set (up to 2 minutes)...")

                cf_cookie = None
                for _ in range(120):  # 2 minutes timeout
                    cookies = context.cookies()
                    cf_cookie = next((c for c in cookies if c['name'] == 'cf_clearance'), None)
                    if cf_cookie:
                        break
                    time.sleep(1)

                if cf_cookie:
                    cf_clearance = cf_cookie['value']
                    user_agent = page.evaluate("navigator.userAgent")

                    logger.info("Successfully fetched cf_clearance and User-Agent from browser.")

                    # Update config
                    self.config["cf_clearance"] = cf_clearance
                    self.config["user_agent"] = user_agent

                    from anime_downloader.utils.config_manager import save_config
                    save_config(self.config)

                    self.session_cookie = f"cf_clearance={cf_clearance}"
                    self.http = self._build_session()
                    browser.close()
                    return True
                else:
                    logger.error("Failed to get cf_clearance cookie within the timeout.")
                    browser.close()
                    return False
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return False
        finally:
            self._browser_challenge_active = False

    def startup_probe(self, url: Optional[str] = None) -> Optional[str]:
        """Probe the current base host and refresh cookies/host before normal requests.

        Returns a retry URL when the probe discovers a better host, otherwise None.
        """
        current_base = constants.get_base_url().rstrip("/")
        probe_url = url or f"{current_base}/"
        parsed_probe = urlparse(probe_url)
        root_url = f"{parsed_probe.scheme}://{parsed_probe.netloc}/"

        logger.info(f"Running startup probe against: {root_url}")

        try:
            raw = self.http.get(root_url, timeout=60, allow_redirects=False)
            response = _CffiResponseWrapper(raw)
        except Exception as e:
            logger.warning(f"Startup probe failed for {root_url}: {e}")
            return None

        try:
            self._capture_set_cookie_headers(response)

            status = getattr(response, "status", None)
            if status == 403:
                logger.warning("Cloudflare challenge detected (403) during probe.")
                if self._fetch_clearance_via_browser():
                    logger.info("Retrying probe after solving challenge...")
                    try:
                        response.close()
                    except Exception:
                        pass
                    return self.startup_probe(url)

            if status in (301, 302, 303, 307, 308):
                location = response.headers.get("location") or response.headers.get("Location")
                if location:
                    redirect_url = urljoin(root_url, location)
                    parsed_redirect = urlparse(redirect_url)
                    new_base = f"{parsed_redirect.scheme}://{parsed_redirect.netloc}"
                    if parsed_redirect.netloc and new_base != current_base:
                        constants.set_base_url(new_base)
                        logger.info(f"Startup probe discovered new base URL: {new_base}")

                    if parsed_probe.path and parsed_probe.path != "/":
                        retry_url = urlunparse(
                            parsed_probe._replace(
                                scheme=parsed_redirect.scheme,
                                netloc=parsed_redirect.netloc,
                            )
                        )
                        logger.info(f"Startup probe will retry on: {retry_url}")
                        return retry_url

            cookie_domain = None
            set_cookie_hdr = response.headers.get("set-cookie") or response.headers.get(
                "Set-Cookie"
            )
            if set_cookie_hdr:
                match = re.search(r"Domain=([^;\s,]+)", set_cookie_hdr, re.IGNORECASE)
                if match:
                    cookie_domain = match.group(1).lstrip(".")

            if cookie_domain and cookie_domain != parsed_probe.netloc:
                new_base = f"{parsed_probe.scheme}://{cookie_domain}"
                constants.set_base_url(new_base)
                logger.info(f"Startup probe discovered cookie host: {new_base}")
                if parsed_probe.path and parsed_probe.path != "/":
                    retry_url = urlunparse(parsed_probe._replace(netloc=cookie_domain))
                    logger.info(f"Startup probe will retry on: {retry_url}")
                    return retry_url

            return None
        finally:
            try:
                response.close()
            except Exception:
                pass

    # Return type annotated as Any to accommodate urllib3's BaseHTTPResponse hierarchy without strict mismatch
    def _request(self, url: str, redirect_count: int = 0) -> Optional[Any]:
        """
        Makes a GET request with retries and exponential backoff.

        Args:
            url (str): The URL to request.

        Returns:
            Optional[Any]: Response object or None.
        """

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logger.debug(f"Making request to: {url}")

        MAX_REDIRECTS = 5

        for attempt in range(constants.MAX_RETRIES):
            try:
                raw = self.http.get(url, timeout=60, allow_redirects=False)
                response = _CffiResponseWrapper(raw)
                status = response.status

                # Successful response
                if status == 200:
                    if logging.getLogger().isEnabledFor(logging.DEBUG):
                        logger.debug(f"Request successful: {url} (status: {status})")
                    return response

                if status == 403:
                    logger.warning(f"Cloudflare challenge detected (403) for {url}.")
                    if self._fetch_clearance_via_browser():
                        logger.info("Retrying request after solving challenge...")
                        try:
                            response.close()
                        except Exception:
                            pass
                        continue # Retry the loop

                # Handle redirects (follow and guard against loops)
                if status in (301, 302, 303, 307, 308):
                    print(f"Received redirect (status {status}) for {url}")
                    location = response.headers.get("location") or response.headers.get("Location")
                    if not location:
                        logger.error("Redirect without Location header")
                        try:
                            response.close()
                        except Exception:
                            pass
                        return None

                    if redirect_count >= MAX_REDIRECTS:
                        logger.error(f"Max redirects ({MAX_REDIRECTS}) reached for {url}")
                        try:
                            response.close()
                        except Exception:
                            pass
                        return None

                    redirect_url = urljoin(url, location)
                    logger.info(f"Following redirect to: {redirect_url}")
                    try:
                        response.close()
                    except Exception:
                        pass
                    return self._request(redirect_url, redirect_count + 1)

                # Forbidden -> probe the site's root for a canonical redirect and follow it (no config changes)
                if status == 403:
                    try:
                        body = response.data
                        try:
                            snippet = body[:400].decode("utf-8", errors="replace")
                        except Exception:
                            snippet = str(body)[:400]
                        logger.warning(
                            f"Received status code 403 for {url}. Headers: {dict(response.headers)} Body snippet: {snippet}"
                        )
                    except Exception:
                        logger.warning(f"Received status code 403 for {url}.")

                    try:
                        response.close()
                    except Exception:
                        pass

                    retry_url = self.startup_probe(url)
                    if retry_url:
                        return self._request(retry_url, redirect_count + 1)

                    # Nothing to follow; fall through to retry/backoff
                    continue

                # Other non-200 status codes
                try:
                    body = response.data
                    try:
                        snippet = body[:400].decode("utf-8", errors="replace")
                    except Exception:
                        snippet = str(body)[:400]
                    logger.warning(
                        f"Received status code {status} for {url}. Headers: {dict(response.headers)} Body snippet: {snippet}"
                    )
                except Exception:
                    logger.warning(f"Received status code {status} for {url}.")
                try:
                    response.close()
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"A network error occurred: {e}")
                if not isinstance(e, (ConnectionError, TimeoutError, OSError)):
                    logger.error(f"An unexpected error occurred: {e}")
                    return None  # Don't retry on unexpected errors

            if attempt < constants.MAX_RETRIES - 1:
                sleep_time = constants.BACKOFF_FACTOR ** (attempt + 1)
                logger.info(
                    f"Retrying in {sleep_time} seconds... ({attempt + 1}/{constants.MAX_RETRIES})"
                )
                time.sleep(sleep_time)
            else:
                logger.error(f"Failed to download {url} after {constants.MAX_RETRIES} attempts.")
                return None

        return None

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Searches for anime on AnimePahe.
        Preferentially uses the local cache which contains the full anime list,
        avoiding the API's pagination limits (approx 8 items).

        Args:
            query (str): The search query.

        Returns:
            List[Dict[str, str]]: List of search result dicts.
        """
        search_results = []

        # Try content from cache first
        try:
            if os.path.exists(constants.ANIME_LIST_CACHE_FILE):
                with open(constants.ANIME_LIST_CACHE_FILE, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            slug, title = line.split("::::", 1)
                        except ValueError:
                            continue

                        if not query or query.lower() in title.lower():
                            search_results.append({"session": slug, "title": title})

                # If we found matches (or query was empty and we got list), return local results
                # Only return if we actually found something. If not, maybe fallback to API?
                # But if cache exists and we found nothing, API probably won't find it either unless cache is stale.
                # Given API limits, cache is better source of truth.
                if search_results:
                    return search_results

                if not query and not search_results:
                    # Empty cache file?
                    return []

        except Exception as e:
            logger.warning(f"Error reading anime cache: {e}")

        if not query:
            logger.warning(
                "Anime list cache not found or empty. Please run with --update-cache first."
            )
            return []

        # Fallback to API if cache didn't exist or had error (or maybe no results found locally)
        # Note: If cache existed but had 0 matches, we still fall back to API here just in case
        # the cache is stale and API has new show.
        response = self._request(f"{constants.SEARCH_URL}&q={query}")
        if response:
            data = json.loads(response.data)
            return data.get("data", [])
        return []

    def fetch_episode_data(self, anime_name: str, anime_slug: str) -> List[Dict[str, Any]]:
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
        all_episodes: List[Dict[str, Any]] = data.get("data", [])

        for page_num in range(2, last_page + 1):
            page_url = f"{constants.RELEASE_URL}&id={anime_slug}&sort=episode_asc&page={page_num}"
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
            logger.warning(f"Audio '{audio}' not found. Selecting from available audio languages.")
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
            logger.warning("Failed to download anime list. Using existing cache if available.")
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
