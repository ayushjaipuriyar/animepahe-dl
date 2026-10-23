# Copilot instructions for animepahe-dl

## Project overview

AnimePahe Downloader is a Python 3.8+ application with both CLI and PyQt6 GUI
front ends. The installed `animepahe-dl` command points to
`anime_downloader.main:main`; `python -m anime_downloader` is also supported.
The `--gui` flag is handled by the dispatcher before the CLI parser is loaded,
so PyQt6 is imported only for GUI launches.

## Build, test, and quality commands

Use `uv` for the development environment. Install the development dependencies
with:

```bash
uv sync --dev --all-extras
```

The application also expects system tools for some paths: `ffmpeg`, `fzf`, and
Node.js are checked by the CLI; a media player is needed only for `--play`.
Linux GUI/CI runs may additionally need the Qt libraries listed in
`.github/workflows/ci.yml`.

Run the configured test suite:

```bash
uv run pytest
```

Pytest is configured in `pyproject.toml` to discover `tests/`, run with strict
markers, and collect coverage for `anime_downloader` by default. Useful focused
commands are:

```bash
# One test module
uv run pytest tests/test_cli.py -v

# One test function or matching group
uv run pytest tests/test_models.py::TestEpisode::test_episode_creation -v
uv run pytest -k "episode"

# Coverage report
uv run pytest --cov=anime_downloader --cov-report=term-missing
```

Before submitting changes, use the project-configured formatters, linter, type
checker, and security scan:

```bash
uv run black anime_downloader tests
uv run isort anime_downloader tests
uv run ruff check anime_downloader tests
uv run mypy anime_downloader --ignore-missing-imports
uv run bandit -r anime_downloader
```

The same checks are wired into `.pre-commit-config.yaml`; run all hooks with
`uv run pre-commit run --all-files` when pre-commit is installed. CI currently
runs `uv sync --dev --all-extras` and `uv run pytest` on Python 3.11 across
Ubuntu, Windows, and macOS.

## Architecture

- `anime_downloader/main.py` is the process entry point. It loads the user
  configuration, applies a configurable AnimePahe base URL, and dispatches to
  either `cli/commands.py` or `gui/main_window.py`.
- `api/client.py` contains `AnimePaheAPI`, the network/site integration layer.
  It searches AnimePahe, fetches anime and episode data, obtains stream and
  playlist URLs, manages cookies/Cloudflare browser challenges, and exposes
  request behavior through a curl_cffi session. Keep site-specific parsing and
  HTTP behavior here rather than in UI code.
- `api/downloader.py` contains the shared media pipeline after a playlist is
  known: save the m3u8, fetch/decrypt AES-128 HLS segments concurrently, and
  compile them with ffmpeg. It is intentionally independent of PyQt so CLI and
  GUI workers can reuse it.
- `models/models.py` defines the shared dataclasses and enums (`Anime`,
  `Episode`, `DownloadTask`, download statuses, quality, and audio language).
  These objects are the boundary between API results, UI state, and persisted
  data.
- `cli/commands.py` owns argument parsing, fzf/questionary interaction,
  episode selection, update checks, downloads, streaming, and daemon commands.
  `gui/main_window.py` owns presentation; long-running GUI work belongs in the
  `QThread` workers in `gui/workers.py`, which communicate through Qt signals.
- `services/cache_service.py` manages JSON caches with TTLs; the API/client and
  CLI use these caches to avoid repeated searches and anime-detail requests.
  `services/daemon_service.py` reuses the API/downloader and CLI update-check
  logic for periodic background downloads and notifications.
- `utils/config_manager.py` creates and merges the user `config.json`;
  `utils/constants.py` derives platform data/download paths and shared HTTP
  settings. Runtime configuration and caches live outside the repository
  (normally under the platform-specific application-data directory described
  in the README).
- `core/` contains domain exceptions and signal/shutdown handling. Prefer
  these exceptions and the shared logger over ad-hoc error types or prints in
  core application code.

## Repository-specific conventions

- Preserve Python 3.8 compatibility. The package metadata and Black/Ruff/mypy
  configuration target Python 3.8 even though CI currently exercises Python
  3.11.
- Keep the CLI and GUI on the same API/downloader implementations. Add shared
  behavior below the front ends instead of duplicating network, playlist,
  decryption, or output-path logic.
- Download paths are constructed through the helpers in
  `cli/commands.py`: anime names are sanitized, each anime has its own
  directory, and each episode has a temporary segment directory plus a final
  `"<sanitized name> Episode <number>.mp4"` output. Preserve this layout for
  resume support.
- Resume behavior depends on existing playlist and segment files. Avoid
  changing filenames, segment-directory semantics, or compilation order
  without updating both CLI and GUI flows.
- Anime and episode persistence goes through `Anime.to_dict()` and
  `Anime.from_dict()`; preserve enum string values and ISO datetime handling
  when changing the model schema.
- New GUI network/download work must run in a `QThread` worker and report
  progress/errors through the worker's Qt signals, not block the main window.
- Use `config_manager.load_config()`/`save_config()` and extend
  `DEFAULT_CONFIG` when adding settings so existing user configurations gain
  defaults safely. Do not commit user config, cookies, cache files, downloads,
  or generated build artifacts.
- Use the shared `utils.logger` for application diagnostics. API and service
  failures should remain observable; do not turn errors into successful-looking
  empty results without following the surrounding logging/error convention.
- Tests use pytest fixtures and mocks to isolate API/downloader and filesystem
  behavior. Follow the existing test modules in `tests/` and avoid requiring
  live AnimePahe access for unit tests.
- Format with Black and isort using the Black profile and 100-character line
  length. Ruff includes pycodestyle, pyflakes, isort, comprehensions,
  bugbear, and pyupgrade rules as configured in `pyproject.toml`.
- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, etc.). Release
  automation uses commit types to determine semantic version changes; update
  `CHANGELOG.md` when a user-facing change warrants it.

## Packaging and platform integrations

The Python package is built with Hatchling and the wheel includes the
`anime_downloader` package. Packaging/release workflows also build binaries,
Snap, Flatpak, and platform artifacts. Keep changes to entry points,
`pyproject.toml`, `snap/`, `systemd/`, and `scripts/` coordinated when they
affect installation or daemon behavior.
