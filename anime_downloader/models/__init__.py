"""
Data models.

This package contains all data model definitions.
"""

from .models import (
    Anime,
    AudioLanguage,
    DownloadProgress,
    DownloadStatus,
    Episode,
    Quality,
    SearchResult,
)

__all__ = [
    "Anime",
    "Episode",
    "Quality",
    "AudioLanguage",
    "DownloadStatus",
    "SearchResult",
    "DownloadProgress",
]
