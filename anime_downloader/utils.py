"""
Utility functions and decorators for the anime downloader.

This module provides common utilities like retry logic, validation,
and helper functions used across the application.
"""

import functools
import time
from typing import Any, Callable, Optional, Type, Tuple
from pathlib import Path

from .logger import logger


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay between retries in seconds.
        backoff: Multiplier for delay after each retry.
        exceptions: Tuple of exception types to catch.
        on_retry: Optional callback function(exception, attempt_number).

    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def unstable_function():
            # May fail occasionally
            pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    if on_retry:
                        on_retry(e, attempt)
                    else:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )

                    time.sleep(current_delay)
                    current_delay *= backoff

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def validate_episode_number(episode_num: Any) -> bool:
    """
    Validate if episode number is valid.

    Args:
        episode_num: Episode number to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        num = int(episode_num)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_quality(quality: str) -> bool:
    """
    Validate if quality setting is valid.

    Args:
        quality: Quality string to validate.

    Returns:
        True if valid, False otherwise.
    """
    valid_qualities = ["best", "1080", "720", "480", "360"]
    return quality in valid_qualities or quality.isdigit()


def validate_audio(audio: str) -> bool:
    """
    Validate if audio setting is valid.

    Args:
        audio: Audio language to validate.

    Returns:
        True if valid, False otherwise.
    """
    return audio in ["jpn", "eng"]


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human-readable string.

    Args:
        bytes_count: Number of bytes.

    Returns:
        Formatted string (e.g., "1.5 GB", "500 MB").
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_count < 1024.0:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., "1h 30m 45s").
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        path: Directory path.

    Returns:
        Path object.

    Raises:
        OSError: If directory cannot be created.
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def is_valid_url(url: str) -> bool:
    """
    Check if string is a valid URL.

    Args:
        url: URL string to validate.

    Returns:
        True if valid URL, False otherwise.
    """
    try:
        from urllib.parse import urlparse

        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.

    Args:
        text: String to truncate.
        max_length: Maximum length.
        suffix: Suffix to add if truncated.

    Returns:
        Truncated string.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: float = 5.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum calls per second.
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)

        self.last_call = time.time()

    def __call__(self, func: Callable) -> Callable:
        """Use as decorator."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            self.wait()
            return func(*args, **kwargs)

        return wrapper
