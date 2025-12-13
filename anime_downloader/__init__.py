"""
AnimePahe Downloader

A Python application for downloading anime episodes from AnimePahe.
"""

from importlib.metadata import version as get_version

__version__ = get_version("animepahe-dl")

# Main entry points
from .main import main
from .cli import cli_main, run_interactive_mode
from .gui import run_gui

__all__ = ['main', 'cli_main', 'run_interactive_mode', 'run_gui']
