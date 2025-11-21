"""Tests for CLI functionality."""
import pytest
from anime_downloader.cli import parse_episode_selection, get_anime_dir, get_video_path


class TestEpisodeSelection:
    """Test cases for episode selection parsing."""

    def test_single_episode(self):
        """Test parsing single episode."""
        result = parse_episode_selection("5", 10)
        assert result == [5]

    def test_multiple_episodes(self):
        """Test parsing multiple episodes."""
        result = parse_episode_selection("1, 3, 5", 10)
        assert result == [1, 3, 5]

    def test_episode_range(self):
        """Test parsing episode range."""
        result = parse_episode_selection("1-5", 10)
        assert result == [1, 2, 3, 4, 5]

    def test_mixed_selection(self):
        """Test parsing mixed selection."""
        result = parse_episode_selection("1, 3-5, 8", 10)
        assert result == [1, 3, 4, 5, 8]

    def test_reverse_range(self):
        """Test parsing reverse range."""
        result = parse_episode_selection("5-3", 10)
        assert result == [3, 4, 5]

    def test_out_of_range(self):
        """Test handling out of range episodes."""
        result = parse_episode_selection("1, 15, 20", 10)
        assert result == [1]

    def test_invalid_input(self):
        """Test handling invalid input."""
        result = parse_episode_selection("1, abc, 3", 10)
        assert result == [1, 3]

    def test_empty_input(self):
        """Test handling empty input."""
        result = parse_episode_selection("", 10)
        assert result == []


class TestPathHelpers:
    """Test cases for path helper functions."""

    def test_get_anime_dir(self):
        """Test anime directory path generation."""
        path = get_anime_dir("Test Anime", "/downloads")
        assert "Test Anime" in path
        assert "/downloads" in path

    def test_get_video_path(self):
        """Test video file path generation."""
        path = get_video_path("Test Anime", 5, "/downloads")
        assert "Test Anime" in path
        assert "Episode 5" in path
        assert path.endswith(".mp4")
