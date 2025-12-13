"""Tests for data models."""
import pytest
from anime_downloader.models import Anime, Episode, DownloadStatus


class TestEpisode:
    """Test cases for Episode model."""

    def test_episode_creation(self):
        """Test creating an episode."""
        ep = Episode(number=1, session="test-session")
        assert ep.number == 1
        assert ep.session == "test-session"
        assert ep.is_downloaded is False

    def test_episode_downloaded_status(self):
        """Test episode downloaded status."""
        import tempfile
        import os
        
        ep = Episode(number=1, session="test-session")
        assert ep.is_downloaded is False
        
        # Test marking as downloaded with a real file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        try:
            ep.mark_as_downloaded(tmp_path)
            assert ep.is_downloaded is True
            assert ep.status == DownloadStatus.DOWNLOADED
        finally:
            os.unlink(tmp_path)


class TestAnime:
    """Test cases for Anime model."""

    def test_anime_creation(self):
        """Test creating an anime."""
        anime = Anime(name="Test Anime", slug="test-anime")
        assert anime.name == "Test Anime"
        assert anime.slug == "test-anime"
        assert anime.episodes == []

    def test_anime_with_episodes(self):
        """Test anime with episodes."""
        anime = Anime(name="Test Anime", slug="test-anime")
        anime.episodes = [
            Episode(number=2, session="ep2"),
            Episode(number=1, session="ep1"),
            Episode(number=3, session="ep3"),
        ]
        # Episodes should be sorted after __post_init__
        anime.__post_init__()
        assert anime.episodes[0].number == 1
        assert anime.episodes[1].number == 2
        assert anime.episodes[2].number == 3

    def test_get_episode(self):
        """Test getting an episode by number."""
        anime = Anime(name="Test Anime", slug="test-anime")
        anime.episodes = [
            Episode(number=1, session="ep1"),
            Episode(number=2, session="ep2"),
        ]
        ep = anime.get_episode(1)
        assert ep is not None
        assert ep.number == 1
        assert ep.session == "ep1"

    def test_get_nonexistent_episode(self):
        """Test getting a non-existent episode."""
        anime = Anime(name="Test Anime", slug="test-anime")
        ep = anime.get_episode(99)
        assert ep is None
