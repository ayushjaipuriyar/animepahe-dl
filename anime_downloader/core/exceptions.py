"""
Custom exceptions for the AnimePahe Downloader.
"""


class AnimePaheError(Exception):
    """Base exception for all AnimePahe Downloader errors."""
    pass


class NetworkError(AnimePaheError):
    """Raised when network operations fail."""
    pass


class DownloadError(AnimePaheError):
    """Raised when download operations fail."""
    pass


class CompilationError(AnimePaheError):
    """Raised when video compilation fails."""
    pass


class ConfigurationError(AnimePaheError):
    """Raised when configuration is invalid or missing."""
    pass


class APIError(AnimePaheError):
    """Raised when API operations fail."""
    pass


class ValidationError(AnimePaheError):
    """Raised when data validation fails."""
    pass