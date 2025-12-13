"""Tests for helper functions."""
import pytest
from anime_downloader.utils.helper import sanitize_filename


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        assert sanitize_filename("Normal Name") == "Normal Name"

    def test_remove_invalid_chars(self):
        """Test removal of invalid characters."""
        assert sanitize_filename("Name<>:/\\|?*") == "Name"

    def test_remove_leading_dot(self):
        """Test removal of leading dot."""
        assert sanitize_filename(".hidden") == "hidden"

    def test_preserve_valid_chars(self):
        """Test preservation of valid characters."""
        assert sanitize_filename("Name-123 (2023).txt") == "Name-123 (2023).txt"

    def test_remove_quotes(self):
        """Test removal of quotes."""
        assert sanitize_filename('Name "quoted"') == "Name quoted"

    def test_empty_string(self):
        """Test empty string handling."""
        result = sanitize_filename("")
        assert result == ""

    def test_only_invalid_chars(self):
        """Test string with only invalid characters."""
        result = sanitize_filename("<>:/\\|?*")
        assert result == ""
