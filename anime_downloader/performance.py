"""
Performance monitoring and profiling utilities.

This module provides tools for monitoring application performance,
tracking metrics, and identifying bottlenecks.
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from .logger import logger


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    errors: int = 0
    last_call_time: Optional[float] = None

    @property
    def avg_time(self) -> float:
        """Calculate average execution time."""
        return self.total_time / self.total_calls if self.total_calls > 0 else 0.0

    def update(self, execution_time: float, error: bool = False):
        """Update metrics with new execution data."""
        self.total_calls += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.last_call_time = execution_time
        if error:
            self.errors += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_calls": self.total_calls,
            "total_time": self.total_time,
            "avg_time": self.avg_time,
            "min_time": self.min_time if self.min_time != float("inf") else 0.0,
            "max_time": self.max_time,
            "errors": self.errors,
            "last_call_time": self.last_call_time,
        }


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, PerformanceMetrics] = defaultdict(PerformanceMetrics)
        self.enabled = True

    def record(self, name: str, execution_time: float, error: bool = False):
        """
        Record a performance metric.

        Args:
            name: Metric name/identifier.
            execution_time: Execution time in seconds.
            error: Whether an error occurred.
        """
        if self.enabled:
            self.metrics[name].update(execution_time, error)

    def get_metrics(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics.

        Args:
            name: Specific metric name, or None for all metrics.

        Returns:
            Dictionary of metrics.
        """
        if name:
            return {name: self.metrics[name].to_dict()}
        return {k: v.to_dict() for k, v in self.metrics.items()}

    def reset(self, name: Optional[str] = None):
        """
        Reset metrics.

        Args:
            name: Specific metric to reset, or None to reset all.
        """
        if name:
            self.metrics[name] = PerformanceMetrics()
        else:
            self.metrics.clear()

    def print_summary(self):
        """Print a summary of all metrics."""
        if not self.metrics:
            logger.info("No performance metrics recorded")
            return

        logger.info("=== Performance Summary ===")
        for name, metrics in sorted(self.metrics.items()):
            logger.info(
                f"{name}:\n"
                f"  Calls: {metrics.total_calls}\n"
                f"  Total Time: {metrics.total_time:.3f}s\n"
                f"  Avg Time: {metrics.avg_time:.3f}s\n"
                f"  Min Time: {metrics.min_time:.3f}s\n"
                f"  Max Time: {metrics.max_time:.3f}s\n"
                f"  Errors: {metrics.errors}"
            )


# Global performance monitor instance
_monitor = PerformanceMonitor()


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return _monitor


def track_performance(name: Optional[str] = None):
    """
    Decorator to track function performance.

    Args:
        name: Custom name for the metric. Uses function name if None.

    Example:
        @track_performance()
        def slow_function():
            time.sleep(1)
    """

    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error_occurred = False

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = True
                raise
            finally:
                execution_time = time.time() - start_time
                _monitor.record(metric_name, execution_time, error_occurred)

        return wrapper

    return decorator


@contextmanager
def measure_time(name: str):
    """
    Context manager to measure execution time.

    Args:
        name: Name for the measurement.

    Example:
        with measure_time("database_query"):
            # Code to measure
            pass
    """
    start_time = time.time()
    error_occurred = False

    try:
        yield
    except Exception:
        error_occurred = True
        raise
    finally:
        execution_time = time.time() - start_time
        _monitor.record(name, execution_time, error_occurred)


class Timer:
    """Simple timer for measuring elapsed time."""

    def __init__(self, name: Optional[str] = None, auto_log: bool = False):
        """
        Initialize timer.

        Args:
            name: Optional name for the timer.
            auto_log: Whether to automatically log elapsed time.
        """
        self.name = name
        self.auto_log = auto_log
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0

    def start(self):
        """Start the timer."""
        self.start_time = time.time()
        return self

    def stop(self) -> float:
        """
        Stop the timer and return elapsed time.

        Returns:
            Elapsed time in seconds.
        """
        if self.start_time is None:
            return 0.0

        self.elapsed = time.time() - self.start_time
        self.start_time = None

        if self.auto_log:
            name = self.name or "Timer"
            logger.info(f"{name}: {self.elapsed:.3f}s")

        return self.elapsed

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.stop()


def benchmark(func: Callable, iterations: int = 100, warmup: int = 10) -> Dict[str, float]:
    """
    Benchmark a function.

    Args:
        func: Function to benchmark.
        iterations: Number of iterations to run.
        warmup: Number of warmup iterations.

    Returns:
        Dictionary with benchmark results.
    """
    # Warmup
    for _ in range(warmup):
        func()

    # Benchmark
    times = []
    for _ in range(iterations):
        start = time.time()
        func()
        times.append(time.time() - start)

    return {
        "iterations": iterations,
        "total_time": sum(times),
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "median_time": sorted(times)[len(times) // 2],
    }


class DownloadStats:
    """Track download statistics."""

    def __init__(self):
        """Initialize download stats."""
        self.total_bytes = 0
        self.total_segments = 0
        self.failed_segments = 0
        self.start_time = time.time()

    def add_segment(self, bytes_downloaded: int, success: bool = True):
        """
        Add segment statistics.

        Args:
            bytes_downloaded: Number of bytes downloaded.
            success: Whether download was successful.
        """
        self.total_segments += 1
        if success:
            self.total_bytes += bytes_downloaded
        else:
            self.failed_segments += 1

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since start."""
        return time.time() - self.start_time

    @property
    def download_speed(self) -> float:
        """Get download speed in MB/s."""
        if self.elapsed_time == 0:
            return 0.0
        return (self.total_bytes / (1024 * 1024)) / self.elapsed_time

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_segments == 0:
            return 0.0
        successful = self.total_segments - self.failed_segments
        return (successful / self.total_segments) * 100

    def summary(self) -> Dict[str, Any]:
        """Get summary of download stats."""
        return {
            "total_bytes": self.total_bytes,
            "total_mb": self.total_bytes / (1024 * 1024),
            "total_segments": self.total_segments,
            "failed_segments": self.failed_segments,
            "success_rate": self.success_rate,
            "elapsed_time": self.elapsed_time,
            "download_speed_mbps": self.download_speed,
        }
