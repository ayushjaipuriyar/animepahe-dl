#!/usr/bin/env python3
"""
Benchmark script for download performance.

This script measures download performance with different configurations
to help optimize settings.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from anime_downloader.performance import benchmark, DownloadStats, Timer
from anime_downloader.logger import logger


def benchmark_thread_counts(thread_counts: List[int]) -> Dict[int, Dict]:
    """
    Benchmark different thread counts.

    Args:
        thread_counts: List of thread counts to test.

    Returns:
        Dictionary mapping thread count to performance metrics.
    """
    results = {}

    for count in thread_counts:
        logger.info(f"\nBenchmarking with {count} threads...")

        # Simulate download with different thread counts
        def download_simulation():
            time.sleep(0.1 / count)  # Simulate faster with more threads

        result = benchmark(download_simulation, iterations=50, warmup=5)
        results[count] = result

        logger.info(
            f"  Avg time: {result['avg_time']:.4f}s\n"
            f"  Min time: {result['min_time']:.4f}s\n"
            f"  Max time: {result['max_time']:.4f}s"
        )

    return results


def benchmark_quality_settings() -> Dict[str, float]:
    """
    Benchmark different quality settings.

    Returns:
        Dictionary mapping quality to download time.
    """
    qualities = ["360", "720", "1080"]
    results = {}

    for quality in qualities:
        logger.info(f"\nBenchmarking quality: {quality}p")

        # Simulate different download sizes
        size_multiplier = {"360": 1.0, "720": 2.5, "1080": 4.0}

        with Timer(f"Quality {quality}p", auto_log=True) as timer:
            time.sleep(0.1 * size_multiplier[quality])

        results[quality] = timer.elapsed

    return results


def benchmark_concurrent_downloads(max_concurrent: List[int]) -> Dict[int, float]:
    """
    Benchmark concurrent episode downloads.

    Args:
        max_concurrent: List of concurrent download counts to test.

    Returns:
        Dictionary mapping concurrent count to total time.
    """
    results = {}

    for count in max_concurrent:
        logger.info(f"\nBenchmarking {count} concurrent downloads...")

        with Timer(f"{count} concurrent", auto_log=True) as timer:
            # Simulate concurrent downloads
            time.sleep(1.0 / count)

        results[count] = timer.elapsed

    return results


def test_download_stats():
    """Test download statistics tracking."""
    logger.info("\nTesting download statistics...")

    stats = DownloadStats()

    # Simulate downloads
    for i in range(100):
        bytes_downloaded = 1024 * 1024 * (i + 1)  # 1MB per segment
        success = i % 10 != 0  # 10% failure rate
        stats.add_segment(bytes_downloaded, success)
        time.sleep(0.01)

    summary = stats.summary()

    logger.info(
        f"\nDownload Statistics:\n"
        f"  Total MB: {summary['total_mb']:.2f}\n"
        f"  Total Segments: {summary['total_segments']}\n"
        f"  Failed Segments: {summary['failed_segments']}\n"
        f"  Success Rate: {summary['success_rate']:.1f}%\n"
        f"  Elapsed Time: {summary['elapsed_time']:.2f}s\n"
        f"  Speed: {summary['download_speed_mbps']:.2f} MB/s"
    )


def main():
    """Run all benchmarks."""
    logger.info("=" * 60)
    logger.info("AnimePahe Downloader Performance Benchmarks")
    logger.info("=" * 60)

    # Benchmark thread counts
    logger.info("\n### Thread Count Benchmark ###")
    thread_results = benchmark_thread_counts([10, 25, 50, 75, 100])

    # Find optimal thread count
    optimal_threads = min(thread_results.items(), key=lambda x: x[1]["avg_time"])
    logger.info(f"\nOptimal thread count: {optimal_threads[0]}")

    # Benchmark quality settings
    logger.info("\n### Quality Settings Benchmark ###")
    quality_results = benchmark_quality_settings()

    # Benchmark concurrent downloads
    logger.info("\n### Concurrent Downloads Benchmark ###")
    concurrent_results = benchmark_concurrent_downloads([1, 2, 3, 4, 5])

    # Test download stats
    test_download_stats()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Benchmark Summary")
    logger.info("=" * 60)

    logger.info("\nRecommendations:")
    logger.info(f"  - Use {optimal_threads[0]} threads for optimal performance")
    logger.info("  - Use 720p for balance between quality and speed")
    logger.info("  - Download 2-3 episodes concurrently for best throughput")

    logger.info("\nNote: These are simulated benchmarks.")
    logger.info("Run actual downloads to measure real-world performance.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nBenchmark cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Benchmark failed: {e}")
        sys.exit(1)
