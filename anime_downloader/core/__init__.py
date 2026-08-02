"""
Core module containing essential utilities for the AnimePahe Downloader.
"""

from .exceptions import (
    AnimePaheError,
    CompilationError,
    ConfigurationError,
    DownloadError,
    NetworkError,
    ValidationError,
)
from .signal_handler import SignalHandler, register_shutdown_callback, setup_signal_handling

__all__ = [
    "AnimePaheError",
    "NetworkError",
    "DownloadError",
    "CompilationError",
    "ConfigurationError",
    "ValidationError",
    "SignalHandler",
    "setup_signal_handling",
    "register_shutdown_callback",
]
