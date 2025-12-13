"""
Core module containing essential utilities for the AnimePahe Downloader.
"""

from .exceptions import (
    AnimePaheError,
    NetworkError,
    DownloadError,
    CompilationError,
    ConfigurationError,
    ValidationError
)
from .signal_handler import SignalHandler, setup_signal_handling, register_shutdown_callback

__all__ = [
    'AnimePaheError',
    'NetworkError',
    'DownloadError',
    'CompilationError',
    'ConfigurationError',
    'ValidationError',
    'SignalHandler',
    'setup_signal_handling',
    'register_shutdown_callback'
]