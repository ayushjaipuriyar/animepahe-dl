"""Tests for configuration management."""
import json
import pytest
from pathlib import Path
from anime_downloader.utils import config_manager


class TestConfigManager:
    """Test cases for config manager."""

    def test_load_default_config(self, temp_dir, monkeypatch):
        """Test loading default configuration."""
        config_file = temp_dir / "config.json"
        monkeypatch.setattr(config_manager, "CONFIG_FILE_PATH", str(config_file))
        
        config = config_manager.load_config()
        
        assert "quality" in config
        assert "audio" in config
        assert "threads" in config
        assert "download_directory" in config

    def test_save_and_load_config(self, temp_dir, monkeypatch):
        """Test saving and loading configuration."""
        config_file = temp_dir / "config.json"
        monkeypatch.setattr(config_manager, "CONFIG_FILE_PATH", str(config_file))
        
        test_config = {
            "quality": "720",
            "audio": "eng",
            "threads": 50,
            "download_directory": "/test/path"
        }
        
        config_manager.save_config(test_config)
        loaded_config = config_manager.load_config()
        
        assert loaded_config["quality"] == "720"
        assert loaded_config["audio"] == "eng"
        assert loaded_config["threads"] == 50

    def test_corrupted_config_recovery(self, temp_dir, monkeypatch):
        """Test recovery from corrupted config file."""
        config_file = temp_dir / "config.json"
        monkeypatch.setattr(config_manager, "CONFIG_FILE_PATH", str(config_file))
        
        # Write corrupted JSON
        config_file.write_text("{ invalid json }")
        
        # Should load default config and backup corrupted file
        config = config_manager.load_config()
        assert "quality" in config
        assert (temp_dir / "config.json.bak").exists()
