"""
This module handles all interactions with the AnimePahe website and its API.
"""

import atexit
import json
import logging
import os
import re
import subprocess
import time
from http.cookies import SimpleCookie
from typing import Any, Dict, List, Optional, Set, cast
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from anime_downloader.utils import config_manager

from ..models import Anime, Episode
from ..utils import constants, logger
from .browser_client import BrowserSession, looks_like_block, looks_like_challenge


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

        self.config = config_manager.load_config()
        self._browser_sessions: Dict[str, Dict[str, str]] = {}
        self._solved_hosts: Set[str] = set()
        self._challenge_attempts: Dict[str, int] = {}
        self._resolved_ids: Dict[str, str] = {}
        self._referers: Dict[str, str] = {}
        self._browser_session: Optional[BrowserSession] = None
        self._closed = False
        atexit.register(self.close)

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
        if file_path.endswith(".json"):
            import json

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    if isinstance(cookies, list):
                        cookie_pairs = [
                            f"{c['name']}={c['value']}"
                            for c in cookies
                            if "name" in c and "value" in c
                        ]
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
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if not content.startswith("# Netscape"):
                            cookie_str = content
                except Exception as inner_e:
                    logger.error(f"Error reading cookie file: {e}")
        return cookie_str

    def _build_session(
        self,
        cookie: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> cffi_requests.Session:
        """Build a curl_cffi Session that impersonates Chrome's TLS fingerprint.

        When ``user_agent`` comes from a solved browser challenge, only the
        identity that ``cf_clearance`` is bound to is overridden. Layering the
        legacy header set on top would contradict curl_cffi's own Chrome
        client hints and get the cookie rejected.
        """
        # ``curl_cffi`` supports this keyword at runtime, but some installed
        # type stubs do not expose it on ``Session``.
        session = cast(Any, cffi_requests.Session)(impersonate="chrome")
        session.verify = False

        if user_agent:
            session.headers.update({"User-Agent": user_agent})
            if cookie is not None:
                session.headers.update({"Cookie": cookie})
            if referer:
                session.headers.update({"Referer": referer})
            return session

        headers = constants.HTTP_HEADERS.copy()
        selected_user_agent = self.config.get("user_agent", "")
        if selected_user_agent:
            headers["User-Agent"] = selected_user_agent
        headers["Cookie"] = cookie if cookie is not None else self.session_cookie

        session.headers.update(headers)
        return session

    @staticmethod
    def _host_for_url(url: str) -> str:
        """Return the normalized host used to route protected requests."""
        return (urlparse(url).hostname or "").lower()

    def _browser_state_path(self) -> Optional[str]:
        """Return the storage-state path when session persistence is enabled."""
        if self.config.get("browser_session_persistence") != "persistent":
            return None
        return os.path.join(constants.BASE_DATA_DIR, "browser_state.json")

    def _get_browser_session(self) -> BrowserSession:
        """Return the shared browser session, launching it on first use."""
        if self._browser_session is None:
            self._browser_session = BrowserSession(
                storage_state=self._browser_state_path(),
                challenge_timeout=int(self.config.get("challenge_timeout", 180)),
            )
        return self._browser_session

    def _session_for_url(self, url: str) -> cffi_requests.Session:
        """Return a session carrying the cookies belonging to the URL host."""
        host = self._host_for_url(url)
        state = self._browser_sessions.get(host)
        if not state:
            parents = [h for h in self._browser_sessions if host.endswith(f".{h}")]
            if parents:
                state = self._browser_sessions[max(parents, key=len)]
        if state:
            return self._build_session(state["cookie"], state["user_agent"], self._referer_for(url))
        return self.http

    def set_referer(self, url: str, referer: str) -> None:
        """Remember which page a host expects requests to be referred from."""
        self._referers[self._host_for_url(url)] = referer

    def _referer_for(self, url: str) -> Optional[str]:
        """Return the recorded referer for a host, if one was seen."""
        host = self._host_for_url(url)
        if host in self._referers:
            return self._referers[host]
        parents = [h for h in self._referers if host.endswith(f".{h}")]
        if parents:
            return self._referers[max(parents, key=len)]
        return None

    def _store_browser_session(
        self, host: str, cookies: List[Dict[str, Any]], user_agent: str
    ) -> None:
        """Store browser cookies per cookie domain and refresh the base session."""
        by_host: Dict[str, List[str]] = {}
        for cookie in cookies:
            name = cookie.get("name")
            value = cookie.get("value")
            if not name or not value:
                continue
            cookie_host = str(cookie.get("domain") or host).lstrip(".").lower()
            if cookie_host != host and not host.endswith(f".{cookie_host}"):
                continue
            by_host.setdefault(cookie_host, []).append(f"{name}={value}")

        if not by_host:
            logger.warning("The browser returned no cookies for {}", host)
            return

        for cookie_host, pairs in by_host.items():
            self._browser_sessions[cookie_host] = {
                "cookie": "; ".join(pairs),
                "user_agent": user_agent,
            }

        base_host = self._host_for_url(constants.get_base_url())
        if base_host in self._browser_sessions and self._browser_sessions[base_host]:
            self.session_cookie = self._browser_sessions[base_host]["cookie"]
            self.config["user_agent"] = self._browser_sessions[base_host]["user_agent"]
            self.http = self._build_session(
                self.session_cookie, self._browser_sessions[base_host]["user_agent"]
            )

    def _solve_challenge(self, url: str) -> bool:
        """Let the user clear the challenge, then reuse that browser session."""
        host = self._host_for_url(url)
        attempts = self._challenge_attempts.get(host, 0)
        limit = int(self.config.get("challenge_attempts", 3))
        if attempts >= limit:
            logger.error(
                "Cloudflare challenged {} {} times in this run; not opening the "
                "browser again. Rerun to try again.",
                host,
                attempts,
            )
            return False
        self._challenge_attempts[host] = attempts + 1

        try:
            browser = self._get_browser_session()
            solved = browser.solve_challenge(url, referer=self._referer_for(url))
        except RuntimeError as e:
            # A missing or mismatched Playwright browser surfaces here.
            logger.error("Could not start the browser: {}", e)
            return False

        if not solved:
            return False

        self._store_browser_session(host, browser.cookies(), browser.user_agent)
        return True

    def _capture_set_cookie_headers(self, response: Any, url: str) -> None:
        """Update the curl session cookie when the base host sets new cookies."""
        if self._host_for_url(url) != self._host_for_url(constants.get_base_url()):
            return
        try:
            set_cookie_hdr = response.headers.get("set-cookie") or response.headers.get(
                "Set-Cookie"
            )
            if not set_cookie_hdr:
                return

            sc = SimpleCookie()
            sc.load(set_cookie_hdr)
            if not sc:
                return

            existing: Dict[str, str] = {}
            for pair in self.session_cookie.split(";"):
                if "=" in pair:
                    name, value = pair.split("=", 1)
                    existing[name.strip()] = value.strip()
            for name, morsel in sc.items():
                existing[name] = morsel.value
            self.session_cookie = "; ".join(f"{name}={value}" for name, value in existing.items())
            self.http = self._build_session()
        except (TypeError, ValueError, AttributeError) as e:
            logger.debug("Could not capture response cookies for {}: {}", url, e)

    def close(self) -> None:
        """Release the browser session, if one was started."""
        if self._closed:
            return
        self._closed = True
        if self._browser_session is not None:
            self._browser_session.close()
            self._browser_session = None

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
            self._capture_set_cookie_headers(response, root_url)

            status = getattr(response, "status", None)
            if looks_like_challenge(status or 0, response.headers, response.data):
                logger.warning("Cloudflare challenge detected during startup probe.")
                if self._solve_challenge(root_url):
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
    def _http_request(self, url: str) -> Optional[Any]:
        """Perform a curl_cffi GET using the session that matches ``url``."""
        last_error: Optional[BaseException] = None
        for attempt in range(constants.MAX_RETRIES):
            try:
                referer = self._referer_for(url)
                response = _CffiResponseWrapper(
                    self._session_for_url(url).get(
                        url,
                        timeout=60,
                        allow_redirects=False,
                        headers={"Referer": referer} if referer else None,
                    )
                )
                self._capture_set_cookie_headers(response, url)
                return response
            except Exception as e:  # noqa: BLE001 - retried below
                last_error = e
                logger.warning("A network error occurred for {}: {}", url, e)

            if attempt < constants.MAX_RETRIES - 1:
                sleep_time = constants.BACKOFF_FACTOR ** (attempt + 1)
                logger.info(
                    "Retrying in {} seconds... ({}/{})",
                    sleep_time,
                    attempt + 1,
                    constants.MAX_RETRIES,
                )
                time.sleep(sleep_time)

        logger.error(
            "Failed to download {} after {} attempts: {}",
            url,
            constants.MAX_RETRIES,
            last_error,
        )
        return None

    def _request(self, url: str, redirect_count: int = 0) -> Optional[Any]:
        """GET ``url``, letting the user clear a Cloudflare challenge if needed.

        A host is only given one interactive attempt per run; a second
        challenge means the exported session is not being accepted and the
        call fails with an actionable message instead of looping.
        """
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logger.debug(f"Making request to: {url}")

        MAX_REDIRECTS = 5
        host = self._host_for_url(url)

        for _ in range(2):
            response = self._http_request(url)
            if response is None:
                return None

            status = response.status
            if not looks_like_challenge(status, response.headers, response.data):
                break

            logger.warning("Cloudflare challenge detected for {}.", url)
            response.close()

            if host in self._solved_hosts:
                logger.error(
                    "{} is still challenging requests after the browser session was "
                    "exported. The host likely requires requests to originate from "
                    "the browser itself.",
                    host,
                )
                return None

            if not self._solve_challenge(url):
                return None
            self._solved_hosts.add(host)

        if response.status == 200:
            return response

        if response.status in (301, 302, 303, 307, 308):
            location = response.headers.get("location") or response.headers.get("Location")
            if not location:
                logger.error("Redirect without Location header")
                response.close()
                return None

            if redirect_count >= MAX_REDIRECTS:
                logger.error("Max redirects ({}) reached for {}", MAX_REDIRECTS, url)
                response.close()
                return None

            redirect_url = urljoin(url, location)
            logger.info("Following redirect to: {}", redirect_url)
            response.close()
            return self._request(redirect_url, redirect_count + 1)

        if looks_like_block(response.status, response.data):
            logger.error(
                "{} refused this request with a Cloudflare block page. That is an "
                "IP/host block rather than a solvable challenge; try another mirror "
                "or network.",
                host,
            )
        else:
            try:
                snippet = response.data[:400].decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - diagnostics only
                snippet = ""
            logger.warning(
                "Received status code {} for {}. Body snippet: {}",
                response.status,
                url,
                snippet,
            )
        response.close()
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

    def resolve_anime_id(self, anime_slug: str) -> str:
        """Return the internal anime id embedded in the anime page.

        The slug used in ``/anime/<slug>`` links is not always the id the
        release API accepts; the page itself declares the real one.
        """
        cached = self._resolved_ids.get(anime_slug)
        if cached:
            return cached

        resolved = anime_slug
        response = self._request(f"{constants.get_base_url()}/anime/{anime_slug}")
        if response:
            match = re.search(
                rb'let\s+id\s*=\s*"([0-9a-fA-F-]{36})"',
                response.data,
            )
            if match:
                resolved = match.group(1).decode("utf-8")

        self._resolved_ids[anime_slug] = resolved
        if resolved != anime_slug:
            logger.info("Resolved anime id {} -> {}", anime_slug, resolved)
        return resolved

    def _release_page(self, anime_id: str, page: int) -> Optional[Dict[str, Any]]:
        """Fetch one page of the release API, or None when it is not JSON."""
        url = f"{constants.RELEASE_URL}&id={anime_id}&sort=episode_asc&page={page}"
        response = self._request(url)
        if not response:
            return None
        try:
            return json.loads(response.data)
        except (ValueError, TypeError):
            return None

    def fetch_episode_data(self, anime_name: str, anime_slug: str) -> List[Dict[str, Any]]:
        """
        Fetches the full list of episodes for a given anime.

        Args:
            anime_name (str): The name of the anime (for logging).
            anime_slug (str): The anime's session ID or page slug.

        Returns:
            List[Dict[str, Any]]: Episode data.
        """
        logger.info(f"Fetching episode list for '{anime_name}'...")
        data = self._release_page(anime_slug, 1)

        if data is None:
            resolved = self.resolve_anime_id(anime_slug)
            if resolved == anime_slug:
                logger.error("Could not read the episode list for {}", anime_name)
                return []
            logger.info("Retrying episode list with the resolved anime id")
            data = self._release_page(resolved, 1)
            if data is None:
                logger.error("Could not read the episode list for {}", anime_name)
                return []
        else:
            self._resolved_ids.setdefault(anime_slug, anime_slug)

        last_page = data.get("last_page", 1)
        all_episodes: List[Dict[str, Any]] = list(data.get("data", []))
        anime_id = self._resolved_ids.get(anime_slug, anime_slug)

        for page_num in range(2, last_page + 1):
            page_data = self._release_page(anime_id, page_num)
            if page_data:
                all_episodes.extend(page_data.get("data", []))

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
        anime_id = self._resolved_ids.get(anime_slug, anime_slug)
        play_url = f"{constants.PLAY_URL}/{anime_id}/{episode_session}"
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
            stream_url = selected_stream.get("url") or ""
            if stream_url:
                self.set_referer(stream_url, play_url)
            return stream_url  # type: ignore[return-value]
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
                        playlist_url = match.group(1) + ".m3u8"
                        self.set_referer(playlist_url, stream_url)
                        return playlist_url
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
