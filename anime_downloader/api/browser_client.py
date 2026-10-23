"""Interactive Cloudflare challenge handling for AnimePahe download hosts.

AnimePahe and the file hosts it redirects to can present a Cloudflare
interstitial that only a human can clear. This module owns one visible
Chromium context, waits for the user to clear the challenge, and exposes the
resulting cookies and User-Agent so the HTTP client can reuse that session.

The challenge itself is always answered by the user; nothing here attempts to
solve it automatically.
"""

import asyncio
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from ..utils import logger

_CHALLENGE_TITLES = (
    "just a moment",
    "attention required",
    "verifying you are human",
    "checking your browser",
    "ddos-guard",
)
_CHALLENGE_BODY_MARKERS = (
    b"Just a moment",
    b"Performing security verification",
    b"Verifying you are human",
    b"cf_chl_opt",
    b"challenge-platform",
    b"cf-browser-verification",
    b"Attention Required",
    b"_cf_chl",
)
_BLOCKED_BODY_MARKERS = (
    b"You have been blocked",
    b"Sorry, you have been blocked",
)


def looks_like_challenge(status: int, headers: Any, body: bytes) -> bool:
    """Return True when a response is a Cloudflare challenge interstitial."""
    mitigated = ""
    try:
        mitigated = (headers.get("cf-mitigated") or headers.get("CF-Mitigated") or "").lower()
    except AttributeError:
        mitigated = ""
    if mitigated == "challenge":
        return True
    if status not in (403, 429, 503):
        return False
    if any(marker in body for marker in _BLOCKED_BODY_MARKERS):
        return False
    return any(marker in body for marker in _CHALLENGE_BODY_MARKERS)


def looks_like_block(status: int, body: bytes) -> bool:
    """Return True when Cloudflare refuses the request instead of challenging."""
    if status not in (403, 429, 503):
        return False
    return any(marker in body for marker in _BLOCKED_BODY_MARKERS)


def _is_challenge_text(title: str, text: str) -> bool:
    """Return True when the page title/text still shows a challenge."""
    haystack = f"{title}\n{text}".lower()
    return any(marker in haystack for marker in _CHALLENGE_TITLES) or (
        "performing security verification" in haystack
    )


def browser_install_hint() -> str:
    """Return the command that installs the browser for *this* environment."""
    import sys

    return (
        "\n\nInstall Playwright's browser for the environment running this tool:\n"
        f"  {sys.executable} -m playwright install chromium\n"
        "Each Python environment pins its own Chromium revision, so install it "
        "from the interpreter that runs the downloader."
    )


class BrowserSession:
    """Owns one visible Chromium context on a private asyncio loop thread."""

    def __init__(
        self,
        storage_state: Optional[str] = None,
        challenge_timeout: int = 180,
        headless: bool = False,
    ) -> None:
        self.storage_state_path = storage_state
        self.challenge_timeout = challenge_timeout
        self.headless = headless
        self.user_agent = ""

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._blocked = False
        self._error: Optional[BaseException] = None
        self._lock = threading.Lock()

        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    def start(self) -> None:
        """Launch the browser on a background event loop, if not already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return

            self._ready.clear()
            self._error = None
            self._thread = threading.Thread(
                target=self._run_loop, name="animepahe-browser", daemon=True
            )
            self._thread.start()

        if not self._ready.wait(timeout=60):
            raise RuntimeError("Timed out while starting the Playwright browser")
        if self._error is not None:
            raise RuntimeError(
                f"Could not start the Playwright browser: {self._error}" + browser_install_hint()
            )

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._bootstrap())
        except BaseException as e:  # noqa: BLE001 - reported to the caller
            self._error = e
            self._ready.set()
            # A partially started Playwright leaves a connection task running;
            # stop it before closing the loop to avoid a "Task was destroyed"
            # warning at shutdown.
            if self._playwright is not None:
                try:
                    loop.run_until_complete(self._playwright.stop())
                except Exception:  # noqa: BLE001
                    pass
            self._playwright = None
            loop.close()
            # Leave no half-built loop behind: close() and a later start()
            # must both behave as if the browser was never launched.
            self._loop = None
            self._thread = None
            return
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            loop.close()
            self._loop = None

    async def _bootstrap(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        context_args: Dict[str, Any] = {}
        if self.storage_state_path and os.path.isfile(self.storage_state_path):
            context_args["storage_state"] = self.storage_state_path
        self._context = await self._browser.new_context(**context_args)

        page = await self._context.new_page()
        try:
            self.user_agent = await page.evaluate("navigator.userAgent")
        finally:
            await page.close()

    def _submit(self, coro: Any, timeout: float) -> Any:
        if self._loop is None:
            raise RuntimeError("Browser event loop is not running")
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout=timeout)

    def solve_challenge(self, url: str, reason: str = "", referer: Optional[str] = None) -> bool:
        """Open ``url`` and wait for the user to finish the challenge there."""
        self.start()
        logger.info(
            "A Cloudflare challenge is blocking {}{}.",
            url,
            f" ({reason})" if reason else "",
        )
        self._blocked = False
        logger.info(
            "A browser window is open. Complete the challenge there; "
            "the download continues automatically once it passes."
        )
        try:
            solved = self._submit(self._solve(url, referer), self.challenge_timeout + 60)
        except Exception as e:  # noqa: BLE001 - surfaced to the caller
            logger.error("Browser challenge window failed: {}", e)
            return False

        if solved:
            self.save_storage_state()
            logger.success("Challenge cleared for {}", url)
        elif not self._blocked:
            logger.error(
                "Challenge was not completed within {} seconds for {}. "
                "Rerun and finish it in the browser window.",
                self.challenge_timeout,
                url,
            )
        return bool(solved)

    async def _solve(self, url: str, referer: Optional[str] = None) -> bool:
        page = await self._context.new_page()
        try:
            if referer:
                # File hosts only offer a solvable challenge when the visit
                # carries the referring page; direct visits get blocked.
                await self._context.set_extra_http_headers({"Referer": referer})
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except Exception as e:  # noqa: BLE001 - navigation may time out mid-challenge
                logger.debug("Initial navigation for challenge did not settle: {}", e)

            deadline = time.monotonic() + self.challenge_timeout
            while time.monotonic() < deadline:
                try:
                    title = await page.title()
                    text = await page.evaluate(
                        "() => document.body ? document.body.innerText.slice(0, 300) : ''"
                    )
                except Exception:  # noqa: BLE001 - the challenge reloads the page
                    await asyncio.sleep(1)
                    continue

                lowered = f"{title}\n{text}".lower()
                if "sorry, you have been blocked" in lowered or "unable to access" in lowered:
                    logger.error(
                        "{} returned a Cloudflare block page. This is an IP/host "
                        "block, not a challenge you can solve in the browser.",
                        url,
                    )
                    self._blocked = True
                    return False

                if title and not _is_challenge_text(title, text):
                    return True
                await asyncio.sleep(1)
            return False
        finally:
            try:
                await page.close()
            except Exception:  # noqa: BLE001 - closing a crashed page must not fail the flow
                pass
            if referer:
                try:
                    await self._context.set_extra_http_headers({})
                except Exception:  # noqa: BLE001
                    pass

    def cookies(self) -> List[Dict[str, Any]]:
        """Return the cookies currently held by the browser context."""
        self.start()
        return list(self._submit(self._context.cookies(), 30))

    def save_storage_state(self) -> bool:
        """Persist the browser session if a storage-state path is configured."""
        if not self.storage_state_path:
            return False
        try:
            state = self._submit(self._context.storage_state(), 30)
            with open(self.storage_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
            try:
                os.chmod(self.storage_state_path, 0o600)
            except OSError as e:
                logger.warning("Could not restrict permissions on browser state: {}", e)
            return True
        except Exception as e:  # noqa: BLE001 - persistence is best effort
            logger.warning("Could not persist browser state: {}", e)
            return False

    async def _shutdown(self) -> None:
        for target in (self._context, self._browser):
            try:
                if target is not None:
                    await target.close()
            except Exception as e:  # noqa: BLE001
                logger.debug("Error while closing browser target: {}", e)
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception as e:  # noqa: BLE001
            logger.debug("Error while stopping Playwright: {}", e)

    def close(self) -> None:
        """Close the browser, saving state first when persistence is enabled."""
        loop = self._loop
        self._context = None
        self._browser = None
        self._playwright = None

        if loop is None or not loop.is_running():
            # The browser never started, or its loop already stopped.
            self._loop = None
            return

        try:
            self.save_storage_state()
        except Exception as e:  # noqa: BLE001 - shutdown is best effort
            logger.debug("Could not save browser state on close: {}", e)

        coro = self._shutdown()
        try:
            asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=30)
        except Exception as e:  # noqa: BLE001
            coro.close()
            logger.debug("Error while shutting the browser down: {}", e)
        finally:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError as e:
                logger.debug("Browser loop was already stopped: {}", e)
            self._loop = None
