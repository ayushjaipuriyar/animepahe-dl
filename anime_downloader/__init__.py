"""
AnimePahe Downloader

A Python application for downloading anime episodes from AnimePahe.
"""

__version__ = "5.6.0-dev.1"

# Main entry points
from .main import main
from .cli import cli_main, run_interactive_mode
from .gui import run_gui

__all__ = ['main', 'cli_main', 'run_interactive_mode', 'run_gui']
