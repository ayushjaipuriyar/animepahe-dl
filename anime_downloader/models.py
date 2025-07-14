"""
Data models for the AnimePahe Downloader.

This module defines the data classes used to represent anime and episodes,
providing a structured way to handle and pass around data within the application.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Episode:
    """
    Represents a single anime episode.

    Attributes:
        number: The episode number (e.g., 1, 2, 3).
        session: The unique session ID for the episode on AnimePahe.
        is_downloaded: A boolean indicating if the episode has been downloaded.
    """
    number: int
    session: str
    is_downloaded: bool = False


@dataclass
class Anime:
    """
    Represents an anime series.

    Attributes:
        name: The title of the anime.
        slug: The unique session ID (slug) for the anime series on AnimePahe.
        episodes: A list of Episode objects belonging to this anime.
        source_file_path: Optional path to the source file this anime was loaded from.
    """
    name: str
    slug: str
    episodes: List[Episode] = field(default_factory=list)
    source_file_path: Optional[str] = None

    def __post_init__(self):
        """Sorts episodes by number after the object is initialized."""
        self.episodes.sort(key=lambda e: e.number)

    def get_episode(self, episode_number: int) -> Optional[Episode]:
        """
        Finds and returns an episode by its number.

        Args:
            episode_number: The number of the episode to find.

        Returns:
            The Episode object if found, otherwise None.
        """
        for episode in self.episodes:
            if episode.number == episode_number:
                return episode
        return None
