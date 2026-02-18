"""
Version helpers for runtime display.
"""

from importlib.metadata import PackageNotFoundError, version as get_version
from pathlib import Path
import re


def _read_version_from_init() -> str:
    init_path = Path(__file__).resolve().parents[1] / "__init__.py"
    try:
        text = init_path.read_text(encoding="utf-8")
    except OSError:
        return "0.0.0"

    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if match:
        return match.group(1)

    return "0.0.0"


def get_app_version() -> str:
    """Return the installed package version or a fallback in frozen builds."""
    try:
        return get_version("animepahe-dl")
    except PackageNotFoundError:
        return _read_version_from_init()
