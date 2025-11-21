"""
Async downloader for improved performance.

This module provides async/await based downloading for better
concurrency and resource utilization.
"""

import asyncio
import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from urllib.parse import urlparse

import urllib3
from Crypto.Cipher import AES

from . import config
from .cache import get_cache
from .logger import logger


class AsyncSegmentDownloader:
    """Async downloader for HLS segments with connection pooling."""

    def __init__(self, max_concurrent: int = 50):
        """
        Initialize async downloader.

        Args:
            max_concurrent: Maximum concurrent downloads.
        """
        self.max_concurrent = max_concurrent
        self.http = urllib3.PoolManager(
            num_pools=10,
            maxsize=max_concurrent,
            headers=config.HTTP_HEADERS,
            cert_reqs="CERT_NONE",
            assert_hostname=False,
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.cache = get_cache()

    async def download_segment(
        self, url: str, key: bytes, iv: bytes, output_path: str
    ) -> Tuple[bool, int]:
        """
        Download and decrypt a single segment asynchronously.

        Args:
            url: Segment URL.
            key: AES decryption key.
            iv: AES initialization vector.
            output_path: Output file path.

        Returns:
            Tuple of (success, bytes_downloaded).
        """
        # Skip if already exists
        if os.path.exists(output_path):
            try:
                return True, os.path.getsize(output_path)
            except OSError:
                return False, 0

        async with self.semaphore:
            # Run blocking I/O in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._download_segment_sync, url, key, iv, output_path
            )

    def _download_segment_sync(
        self, url: str, key: bytes, iv: bytes, output_path: str
    ) -> Tuple[bool, int]:
        """Synchronous segment download (runs in executor)."""
        try:
            response = self.http.request("GET", url, preload_content=False, timeout=30)

            if response.status != 200:
                logger.warning(f"Failed to download segment: HTTP {response.status}")
                return False, 0

            encrypted_data = response.data
            bytes_downloaded = len(encrypted_data)

            # Pad for AES
            while len(encrypted_data) % 16 != 0:
                encrypted_data += b"\0"

            # Decrypt
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = cipher.decrypt(encrypted_data)

            # Write to file
            with open(output_path, "wb") as f:
                f.write(decrypted_data)

            return True, bytes_downloaded

        except Exception as e:
            logger.error(f"Error downloading segment {os.path.basename(output_path)}: {e}")
            return False, 0

    async def download_segments(
        self,
        segments: List[str],
        key: bytes,
        media_sequence: int,
        output_dir: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> bool:
        """
        Download multiple segments concurrently.

        Args:
            segments: List of segment URLs.
            key: AES decryption key.
            media_sequence: Starting media sequence number.
            output_dir: Output directory.
            progress_callback: Optional callback(completed, total, speed_mbps).

        Returns:
            True if all segments downloaded successfully.
        """
        os.makedirs(output_dir, exist_ok=True)

        # Filter already downloaded segments
        tasks = []
        for idx, seg_url in enumerate(segments):
            segment_index = media_sequence + idx
            iv = segment_index.to_bytes(16, byteorder="big")
            segment_name = os.path.basename(urlparse(seg_url).path)
            output_path = os.path.join(output_dir, segment_name)

            tasks.append(self.download_segment(seg_url, key, iv, output_path))

        # Download with progress tracking
        completed = 0
        total_bytes = 0
        start_time = asyncio.get_event_loop().time()

        for coro in asyncio.as_completed(tasks):
            success, bytes_downloaded = await coro
            if success:
                completed += 1
                total_bytes += bytes_downloaded

                if progress_callback:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    speed_mbps = (total_bytes / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    progress_callback(completed, len(tasks), speed_mbps)

        return completed == len(tasks)

    def close(self):
        """Close the HTTP pool."""
        self.http.clear()


async def download_episode_async(
    segments: List[str],
    key: bytes,
    media_sequence: int,
    output_dir: str,
    max_concurrent: int = 50,
    progress_callback: Optional[Callable[[int, int, float], None]] = None,
) -> bool:
    """
    Convenience function to download an episode's segments asynchronously.

    Args:
        segments: List of segment URLs.
        key: AES decryption key.
        media_sequence: Starting media sequence number.
        output_dir: Output directory.
        max_concurrent: Maximum concurrent downloads.
        progress_callback: Optional progress callback.

    Returns:
        True if successful.
    """
    downloader = AsyncSegmentDownloader(max_concurrent=max_concurrent)
    try:
        return await downloader.download_segments(
            segments, key, media_sequence, output_dir, progress_callback
        )
    finally:
        downloader.close()
