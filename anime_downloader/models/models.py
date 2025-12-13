"""
Data models for the AnimePahe Downloader.

This module defines the data classes and models used to represent anime, episodes,
and other entities, providing a structured way to handle and pass around data
within the application.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

from ..core.exceptions import ValidationError


class DownloadStatus(Enum):
    """Enumeration for download status."""
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    PAUSED = "paused"


class Quality(Enum):
    """Enumeration for video quality."""
    BEST = "best"
    Q1080P = "1080"
    Q720P = "720"
    Q480P = "480"
    Q360P = "360"


class AudioLanguage(Enum):
    """Enumeration for audio language."""
    JAPANESE = "jpn"
    ENGLISH = "eng"


@dataclass
class DownloadProgress:
    """Represents download progress information."""
    current: int = 0
    total: int = 0
    percentage: float = 0.0
    speed: float = 0.0  # MB/s
    eta: Optional[int] = None  # seconds
    message: str = ""
    
    def update(self, current: int, total: int, message: str = ""):
        """Update progress information."""
        self.current = current
        self.total = total
        self.percentage = (current / total * 100) if total > 0 else 0.0
        self.message = message


@dataclass
class Episode:
    """
    Represents a single anime episode with enhanced functionality.

    Attributes:
        number: The episode number (e.g., 1, 2, 3).
        session: The unique session ID for the episode on AnimePahe.
        status: Current download status.
        file_path: Path to the downloaded file (if exists).
        file_size: Size of the downloaded file in bytes.
        download_date: When the episode was downloaded.
        progress: Current download progress.
    """
    number: int
    session: str
    status: DownloadStatus = DownloadStatus.NOT_DOWNLOADED
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    download_date: Optional[datetime] = None
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    
    @property
    def is_downloaded(self) -> bool:
        """Check if episode is downloaded."""
        return (self.status == DownloadStatus.DOWNLOADED and 
                self.file_path and os.path.exists(self.file_path))
    
    @property
    def is_downloading(self) -> bool:
        """Check if episode is currently downloading."""
        return self.status == DownloadStatus.DOWNLOADING
    
    def mark_as_downloaded(self, file_path: str):
        """Mark episode as downloaded."""
        self.status = DownloadStatus.DOWNLOADED
        self.file_path = file_path
        self.download_date = datetime.now()
        if os.path.exists(file_path):
            self.file_size = os.path.getsize(file_path)
    
    def mark_as_failed(self):
        """Mark episode as failed."""
        self.status = DownloadStatus.FAILED
    
    def reset_download(self):
        """Reset download status."""
        self.status = DownloadStatus.NOT_DOWNLOADED
        self.progress = DownloadProgress()


@dataclass
class Anime:
    """
    Represents an anime series with enhanced functionality.

    Attributes:
        name: The title of the anime.
        slug: The unique session ID (slug) for the anime series on AnimePahe.
        episodes: A list of Episode objects belonging to this anime.
        source_file_path: Optional path to the source file this anime was loaded from.
        metadata: Additional metadata about the anime.
        total_episodes: Total number of episodes (if known).
        year: Release year.
        genres: List of genres.
    """
    name: str
    slug: str
    episodes: List[Episode] = field(default_factory=list)
    source_file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_episodes: Optional[int] = None
    year: Optional[int] = None
    genres: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize anime after creation."""
        self._sort_episodes()
        self._validate()
    
    def _sort_episodes(self):
        """Sort episodes by number."""
        self.episodes.sort(key=lambda e: e.number)
    
    def _validate(self):
        """Validate anime data."""
        if not self.name.strip():
            raise ValidationError("Anime name cannot be empty")
        if not self.slug.strip():
            raise ValidationError("Anime slug cannot be empty")

    def get_episode(self, episode_number: int) -> Optional[Episode]:
        """
        Find and return an episode by its number.

        Args:
            episode_number: The number of the episode to find.

        Returns:
            The Episode object if found, otherwise None.
        """
        for episode in self.episodes:
            if episode.number == episode_number:
                return episode
        return None
    
    def add_episode(self, episode: Episode):
        """Add an episode to the anime."""
        if self.get_episode(episode.number) is None:
            self.episodes.append(episode)
            self._sort_episodes()
    
    def remove_episode(self, episode_number: int) -> bool:
        """Remove an episode by number."""
        episode = self.get_episode(episode_number)
        if episode:
            self.episodes.remove(episode)
            return True
        return False
    
    @property
    def downloaded_episodes(self) -> List[Episode]:
        """Get list of downloaded episodes."""
        return [ep for ep in self.episodes if ep.is_downloaded]
    
    @property
    def pending_episodes(self) -> List[Episode]:
        """Get list of episodes not yet downloaded."""
        return [ep for ep in self.episodes if not ep.is_downloaded]
    
    @property
    def download_progress(self) -> float:
        """Get overall download progress as percentage."""
        if not self.episodes:
            return 0.0
        downloaded = len(self.downloaded_episodes)
        return (downloaded / len(self.episodes)) * 100.0
    
    def get_episode_range(self, start: int, end: int) -> List[Episode]:
        """Get episodes in a specific range."""
        return [ep for ep in self.episodes if start <= ep.number <= end]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert anime to dictionary."""
        return {
            'name': self.name,
            'slug': self.slug,
            'total_episodes': self.total_episodes,
            'year': self.year,
            'genres': self.genres,
            'metadata': self.metadata,
            'episodes': [
                {
                    'number': ep.number,
                    'session': ep.session,
                    'status': ep.status.value,
                    'file_path': ep.file_path,
                    'file_size': ep.file_size,
                    'download_date': ep.download_date.isoformat() if ep.download_date else None
                }
                for ep in self.episodes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Anime':
        """Create anime from dictionary."""
        anime = cls(
            name=data['name'],
            slug=data['slug'],
            total_episodes=data.get('total_episodes'),
            year=data.get('year'),
            genres=data.get('genres', []),
            metadata=data.get('metadata', {})
        )
        
        for ep_data in data.get('episodes', []):
            episode = Episode(
                number=ep_data['number'],
                session=ep_data['session'],
                status=DownloadStatus(ep_data.get('status', 'not_downloaded')),
                file_path=ep_data.get('file_path'),
                file_size=ep_data.get('file_size')
            )
            if ep_data.get('download_date'):
                episode.download_date = datetime.fromisoformat(ep_data['download_date'])
            anime.add_episode(episode)
        
        return anime


@dataclass
class DownloadTask:
    """Represents a download task."""
    anime: Anime
    episode: Episode
    quality: Quality = Quality.BEST
    audio: AudioLanguage = AudioLanguage.JAPANESE
    output_path: str = ""
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def __lt__(self, other):
        """Compare tasks by priority."""
        return self.priority < other.priority


@dataclass
class SearchResult:
    """Represents a search result."""
    title: str
    session: str
    year: Optional[int] = None
    status: Optional[str] = None
    episodes: Optional[int] = None
    
    def to_anime(self) -> Anime:
        """Convert search result to Anime object."""
        return Anime(
            name=self.title,
            slug=self.session,
            total_episodes=self.episodes,
            year=self.year
        )
