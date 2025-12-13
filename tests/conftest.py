"""Pytest configuration and shared fixtures."""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from anime_downloader.api import AnimePaheAPI, Downloader
from anime_downloader.models import Anime, Episode


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_api():
    """Create a mock AnimePaheAPI instance."""
    api = Mock(spec=AnimePaheAPI)
    api.verify_ssl = False
    return api


@pytest.fixture
def mock_downloader(mock_api):
    """Create a mock Downloader instance."""
    return Downloader(mock_api)


@pytest.fixture
def sample_anime():
    """Create a sample Anime object for testing."""
    anime = Anime(name="Test Anime", slug="test-anime")
    anime.episodes = [
        Episode(number=1, session="ep1-session", is_downloaded=False),
        Episode(number=2, session="ep2-session", is_downloaded=True),
        Episode(number=3, session="ep3-session", is_downloaded=False),
    ]
    return anime


@pytest.fixture
def sample_episode():
    """Create a sample Episode object for testing."""
    return Episode(number=1, session="test-session", is_downloaded=False)
