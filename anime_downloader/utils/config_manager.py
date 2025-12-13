"""
Manages loading and creating the user's configuration file.

This module handles the reading and writing of the `config.json` file.
It provides default settings and ensures that a valid configuration is
always available.
"""

import json
import os
from typing import Any, Dict

from . import constants

# The absolute path to the user's configuration file.
CONFIG_FILE_PATH = os.path.join(constants.BASE_DATA_DIR, "config.json")

# Default configuration values for the application.
DEFAULT_CONFIG = {
    "base_url": constants.BASE_URL,  # Allow overriding mirror/domain
    "quality": "best",
    "audio": "jpn",
    "threads": 100,
    "download_directory": os.path.join(constants.BASE_DOWNLOAD_DIR, "Anime"),
    "update_interval_hours": 5,
    "allow_insecure_ssl": True,  # Forced disabled certificate verification per user request
}


def load_config() -> Dict[str, Any]:
    """
    Loads the configuration from config.json.

    If the file doesn't exist, it creates one with default values.
    If the file is corrupted, it backs up the old one and creates a new one.

    Returns:
        A dictionary containing the application configuration.
    """
    os.makedirs(constants.BASE_DATA_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE_PATH):
        print(
            f"Configuration file not found. Creating a default one at: {CONFIG_FILE_PATH}"
        )
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            # Ensure all keys from the default config are present.
            # This makes the config forward-compatible if new keys are added.
            config_to_load = DEFAULT_CONFIG.copy()
            config_to_load.update(user_config)
            return config_to_load
    except (json.JSONDecodeError, TypeError):
        print("Error reading config.json. It might be corrupted.")
        print("Backing up the existing file and creating a new default one.")
        try:
            os.rename(CONFIG_FILE_PATH, f"{CONFIG_FILE_PATH}.bak")
        except OSError as e:
            print(f"Error backing up config file: {e}")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG


def save_config(config_data: Dict[str, Any]):
    """
    Saves the provided configuration data to config.json.

    Args:
        config_data: A dictionary containing the configuration to save.
    """
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error saving configuration to {CONFIG_FILE_PATH}: {e}")
