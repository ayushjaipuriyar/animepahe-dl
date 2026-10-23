"""Tests for challenge detection and browser-session export."""

from types import SimpleNamespace

from anime_downloader.api.browser_client import (
    BrowserSession,
    browser_install_hint,
    looks_like_block,
    looks_like_challenge,
)
from anime_downloader.api.client import AnimePaheAPI

INTERSTITIAL = b"<html><head><title>Just a moment...</title></head><body>cf_chl_opt</body></html>"
BLOCK_PAGE = (
    b"<html><head><title>Attention Required! | Cloudflare</title></head>"
    b"<body>Sorry, you have been blocked</body></html>"
)


def make_api():
    api = AnimePaheAPI.__new__(AnimePaheAPI)
    api.config = {}
    api._browser_sessions = {}
    api._solved_hosts = set()
    api._challenge_attempts = {}
    api._resolved_ids = {}
    api._referers = {}
    api._browser_session = None
    api._closed = False
    api.session_cookie = "initial=value"
    api.http = object()
    return api


def response(status, body=b"", headers=None):
    return SimpleNamespace(status=status, headers=headers or {}, data=body, close=lambda: None)


def test_looks_like_challenge_uses_cf_mitigated_header():
    assert looks_like_challenge(403, {"cf-mitigated": "challenge"}, b"") is True


def test_looks_like_challenge_detects_interstitial():
    assert looks_like_challenge(403, {}, INTERSTITIAL) is True


def test_block_page_is_not_treated_as_solvable_challenge():
    assert looks_like_challenge(403, {}, BLOCK_PAGE) is False


def test_ordinary_success_is_not_a_challenge():
    assert looks_like_challenge(200, {}, b"<html>AnimePahe</html>") is False


def test_cookies_are_scoped_to_the_challenged_host(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "_build_session", lambda *a, **k: "session")

    api._store_browser_session(
        "kiwi.cx",
        [
            {"name": "cf_clearance", "value": "stream", "domain": ".kiwi.cx"},
            {"name": "unrelated", "value": "x", "domain": ".cloudflare.com"},
        ],
        "browser-agent",
    )

    assert api._browser_sessions == {
        "kiwi.cx": {"cookie": "cf_clearance=stream", "user_agent": "browser-agent"}
    }


def test_cookies_for_other_domains_are_not_exported(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "_build_session", lambda *a, **k: "session")

    api._store_browser_session(
        "pahe.win",
        [{"name": "session", "value": "file", "domain": "kiwi.cx"}],
        "browser-agent",
    )

    assert api._browser_sessions == {}


def test_session_for_subdomain_prefers_longest_match(monkeypatch):
    api = make_api()
    api._browser_sessions = {
        "cx": {"cookie": "broad=1", "user_agent": "broad"},
        "kiwi.cx": {"cookie": "specific=1", "user_agent": "specific"},
    }
    monkeypatch.setattr(
        api, "_build_session", lambda cookie, user_agent, referer=None: (cookie, user_agent)
    )

    assert api._session_for_url("https://cdn.kiwi.cx/a.m3u8") == ("specific=1", "specific")


def test_challenge_is_solved_then_request_is_retried(monkeypatch):
    api = make_api()
    responses = [response(403, INTERSTITIAL), response(200, b"playlist")]
    calls = []

    def fake_http(url):
        calls.append(url)
        return responses.pop(0)

    def fake_solve(url):
        api._browser_sessions["pahe.win"] = {"cookie": "cf_clearance=ok", "user_agent": "ua"}
        return True

    monkeypatch.setattr(api, "_http_request", fake_http)
    monkeypatch.setattr(api, "_solve_challenge", fake_solve)

    result = api._request("https://pahe.win/file.m3u8")

    assert result is not None and result.status == 200
    assert calls == ["https://pahe.win/file.m3u8", "https://pahe.win/file.m3u8"]
    assert "pahe.win" in api._solved_hosts


def test_second_challenge_on_same_host_does_not_reopen_browser(monkeypatch):
    api = make_api()
    api._solved_hosts.add("pahe.win")
    solve_calls = []

    monkeypatch.setattr(api, "_http_request", lambda url: response(403, INTERSTITIAL))
    monkeypatch.setattr(api, "_solve_challenge", lambda url: solve_calls.append(url) or True)

    assert api._request("https://pahe.win/file.m3u8") is None
    assert solve_calls == []


def test_failed_challenge_returns_none(monkeypatch):
    api = make_api()
    monkeypatch.setattr(api, "_http_request", lambda url: response(403, INTERSTITIAL))
    monkeypatch.setattr(api, "_solve_challenge", lambda url: False)

    assert api._request("https://pahe.win/file.m3u8") is None


def test_block_page_is_reported_separately():
    assert looks_like_block(403, BLOCK_PAGE) is True
    assert looks_like_block(200, BLOCK_PAGE) is False


def test_challenge_attempts_are_capped(monkeypatch):
    api = make_api()
    api.config = {"challenge_attempts": 2}
    solved = []

    class FakeBrowser:
        user_agent = "ua"

        def solve_challenge(self, url, referer=None):
            solved.append(url)
            return True

        def cookies(self):
            return []

    monkeypatch.setattr(api, "_get_browser_session", lambda: FakeBrowser())
    monkeypatch.setattr(api, "_store_browser_session", lambda *a, **k: None)

    assert api._solve_challenge("https://anon.example/a") is True
    assert api._solve_challenge("https://anon.example/b") is True
    assert api._solve_challenge("https://anon.example/c") is False
    assert len(solved) == 2


def test_resolve_anime_id_reads_page_script():
    api = make_api()
    page = (
        b'<script>let id = "71f5f4d1-8734-9bec-4edb-0c4f737d73f8"; '
        b'let sort = "episode_asc";</script>'
    )
    api._request = lambda url: response(200, page)
    resolved = api.resolve_anime_id("d3a944c3-41a8-efd8-f286-79c1813f6ef2")

    assert resolved == "71f5f4d1-8734-9bec-4edb-0c4f737d73f8"
    assert api._resolved_ids["d3a944c3-41a8-efd8-f286-79c1813f6ef2"] == resolved


def test_episode_fetch_falls_back_to_resolved_id(monkeypatch):
    api = make_api()
    api._resolved_ids = {}
    api._referers = {}
    calls = []

    def fake_request(url):
        calls.append(url)
        if "id=stale-slug" in url:
            return response(404, b"<html>Not found</html>")
        if "/anime/stale-slug" in url:
            return response(
                200, b'<script>let id = "11111111-2222-3333-4444-555555555555";</script>'
            )
        if "id=11111111" in url:
            return response(
                200,
                b'{"last_page": 1, "data": [{"episode": 1, "session": "s1"}]}',
            )
        return response(404, b"")

    monkeypatch.setattr(api, "_request", fake_request)

    episodes = api.fetch_episode_data("Show", "stale-slug")

    assert episodes == [{"episode": 1, "session": "s1"}]
    assert any("id=11111111" in url for url in calls)


def test_referer_is_recorded_per_host_and_matched_for_subdomains():
    api = make_api()
    play = "https://animepahe.pw/play/abc/session"

    api.set_referer("https://kwik.cx/e/xyz", play)

    assert api._referer_for("https://kwik.cx/e/other") == play
    assert api._referer_for("https://cdn.kwik.cx/e/other") == play
    assert api._referer_for("https://unrelated.example/x") is None


def test_http_request_sends_the_recorded_referer(monkeypatch):
    api = make_api()
    captured = {}

    class FakeSession:
        def get(self, url, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(status_code=200, headers={}, content=b"ok")

    monkeypatch.setattr(api, "_session_for_url", lambda url: FakeSession())
    monkeypatch.setattr(api, "_capture_set_cookie_headers", lambda *a: None)
    api.set_referer("https://kwik.cx/e/xyz", "https://animepahe.pw/play/1/2")

    response = api._http_request("https://kwik.cx/e/xyz")

    assert response is not None
    assert captured["headers"] == {"Referer": "https://animepahe.pw/play/1/2"}


def test_browser_install_hint_targets_the_running_interpreter():
    hint = browser_install_hint()

    assert "-m playwright install chromium" in hint
    assert "python" in hint.lower()


def test_close_is_safe_when_the_browser_never_started():
    BrowserSession().close()


def test_solve_challenge_reports_a_missing_browser_without_crashing(monkeypatch):
    api = make_api()
    api.config = {"challenge_attempts": 1}

    class BrokenBrowser:
        def solve_challenge(self, url, referer=None):
            raise RuntimeError("Executable doesn't exist at chromium-1243")

    monkeypatch.setattr(api, "_get_browser_session", lambda: BrokenBrowser())

    assert api._solve_challenge("https://animepahe.pw/") is False
