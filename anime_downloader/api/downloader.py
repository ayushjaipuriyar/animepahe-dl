"""
Handles the core logic for downloading, decrypting, and compiling video segments.

This module provides the `Downloader` class, which is responsible for the entire
download pipeline after the initial API calls have been made. This includes:
- Fetching the m3u8 playlist.
- Parsing the playlist to get segment URLs and the decryption key.
- Downloading individual video segments in parallel.
- Decrypting the AES-128 encrypted segments.
- Compiling the decrypted segments into a final MP4 video file using ffmpeg.
"""

import os
import re
import shutil
import subprocess
import shutil as _shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from urllib.parse import urlparse

from Crypto.Cipher import AES
from tqdm import tqdm

from ..utils import constants, logger
from .client import AnimePaheAPI
from ..core.signal_handler import is_shutdown_requested


class Downloader:
    """
    Manages the download, decryption, and compilation of HLS video streams.

    This class is designed to be a plain Python implementation, independent of
    any specific concurrency model (like PyQt signals), making it reusable
    for both the CLI and GUI.
    """

    def __init__(self, api: AnimePaheAPI):
        """
        Initializes the Downloader.

        Args:
            api: An instance of AnimePaheAPI to handle network requests.
        """
        self.api = api

    def download_segment(
        self, url: str, key: bytes, iv: bytes, output_path: str
    ) -> int:
        """
        Downloads and decrypts a single HLS video segment.

        If the segment already exists on disk, it skips the download.

        Args:
            url: The URL of the .ts video segment to download.
            key: The 16-byte AES decryption key.
            iv: The 16-byte AES initialization vector (IV).
            output_path: The file path to save the decrypted segment to.

        Returns:
            The number of bytes downloaded, or 0 on failure.
        """
        # Skip if the segment is already downloaded
        if os.path.exists(output_path):
            logger.info(f"✓ Resuming: Segment already exists: {os.path.basename(output_path)}")
            try:
                return os.path.getsize(output_path)
            except OSError:
                return 0

        # Verbose logging for debugging
        import logging
        segment_name = os.path.basename(urlparse(url).path)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logger.debug(f"Downloading segment: {segment_name} from {url}")

        # Download the encrypted segment
        try:
            response = self.api._request(url)
            if not response:
                logger.error(f"Failed to download segment: {segment_name}")
                logger.error(f"Segment URL: {url}")
                return 0
        except Exception as e:
            logger.error(f"Error downloading segment {segment_name}: {e}")
            logger.error(f"Segment URL: {url}")
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                import traceback
                logger.debug(f"Full traceback for segment {segment_name}: {traceback.format_exc()}")
            return 0

        encrypted_data = response.data
        bytes_downloaded = len(encrypted_data)

        # Pad data if it's not a multiple of 16 for AES
        while len(encrypted_data) % 16 != 0:
            encrypted_data += b"\0"

        # Decrypt the segment
        try:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = cipher.decrypt(encrypted_data)
            with open(output_path, "wb") as f:
                f.write(decrypted_data)
            return bytes_downloaded
        except Exception as e:
            logger.error(
                f"Failed to decrypt or save segment {os.path.basename(output_path)}: {e}"
            )
            return 0

    def fetch_playlist(self, playlist_url: str, output_dir: str) -> Optional[str]:
        """
        Downloads the master m3u8 playlist file.

        Args:
            playlist_url: The URL of the m3u8 playlist.
            output_dir: The directory to save the playlist in.

        Returns:
            The local path to the downloaded playlist file, or None on failure.
        """
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, "playlist.m3u8")

        if os.path.exists(file_path):
            logger.info(f"Resuming: Playlist already exists: {file_path}")
            return file_path

        response = self.api._request(playlist_url)
        if response:
            with open(file_path, "wb") as f:
                f.write(response.data)
            return file_path
        else:
            logger.error("Failed to download m3u8 playlist.")
            return None

    def get_playlist_details(self, playlist_path: str) -> Optional[dict]:
        """
        Parses an m3u8 playlist to extract segment URLs, the key URL, and total duration.

        Args:
            playlist_path: The local path to the m3u8 playlist file.

        Returns:
            A dictionary containing details, or None if parsing fails.
        """
        if not os.path.exists(playlist_path):
            return None

        key_url, segments, media_sequence, total_duration = "", [], 0, 0.0
        with open(playlist_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#EXT-X-MEDIA-SEQUENCE"):
                    media_sequence = int(line.split(":")[1])
                elif line.startswith("#EXT-X-KEY"):
                    key_url_match = re.search('URI="([^"]+)"', line)
                    if key_url_match:
                        key_url = key_url_match.group(1)
                elif line.startswith("#EXTINF:"):
                    try:
                        total_duration += float(line.split(":")[1].split(",")[0])
                    except (ValueError, IndexError):
                        continue
                elif line.startswith("https"):
                    segments.append(line)

        if not key_url or not segments:
            logger.error("Playlist parsing failed: Could not find key URL or segments.")
            return None

        return {
            "key_url": key_url,
            "segments": segments,
            "media_sequence": media_sequence,
            "duration": total_duration,
        }

    def download_from_playlist_cli(self, playlist_path: str, num_threads: int) -> bool:
        """
        Manages the download of all video segments from a playlist for the CLI.

        This method uses a thread pool to download segments in parallel and displays
        a `tqdm` progress bar to show download speed and progress.

        Args:
            playlist_path: The local path to the m3u8 playlist.
            num_threads: The number of threads to use for downloading.

        Returns:
            True if all segments were downloaded successfully, False otherwise.
        """
        playlist_details = self.get_playlist_details(playlist_path)
        if not playlist_details:
            logger.error(f"Could not parse playlist at {playlist_path}")
            return False

        # Download the decryption key
        key_response = self.api._request(playlist_details["key_url"])
        if not key_response:
            logger.error("Failed to download decryption key.")
            return False
        key = key_response.data

        episode_dir = os.path.dirname(playlist_path)
        segments = playlist_details["segments"]

        # Determine which segments need to be downloaded
        segments_to_download = [
            s
            for s in segments
            if not os.path.exists(
                os.path.join(episode_dir, os.path.basename(urlparse(s).path))
            )
        ]

        if not segments_to_download:
            logger.info("All segments already downloaded.")
            return True

        total_bytes_downloaded = 0
        start_time = time.time()

        with tqdm(
            total=len(segments_to_download), unit="seg", desc="Downloading"
        ) as pbar:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Create a future for each segment download with proper mapping
                future_to_segment = {}
                for seg_url in segments_to_download:
                    original_index = segments.index(seg_url)
                    # The IV for each segment is its sequence number
                    segment_index = playlist_details["media_sequence"] + original_index
                    iv = segment_index.to_bytes(16, byteorder="big")
                    segment_name = os.path.basename(urlparse(seg_url).path)
                    output_path = os.path.join(episode_dir, segment_name)
                    future = executor.submit(
                        self.download_segment, seg_url, key, iv, output_path
                    )
                    future_to_segment[future] = {
                        'url': seg_url,
                        'name': segment_name,
                        'index': original_index
                    }

                # Process completed futures
                failed_segments = []
                for future in as_completed(future_to_segment):
                    if is_shutdown_requested():
                        logger.info("Shutdown requested, stopping segment downloads")
                        break
                    
                    segment_info = future_to_segment[future]
                    segment_name = segment_info['name']
                    seg_url = segment_info['url']
                    
                    try:
                        bytes_downloaded = future.result()
                        if bytes_downloaded > 0:
                            pbar.update(1)
                            total_bytes_downloaded += bytes_downloaded
                            elapsed_time = time.time() - start_time
                            # Calculate and display download speed
                            speed_mbps = (
                                (total_bytes_downloaded / (1024 * 1024)) / elapsed_time
                                if elapsed_time > 0
                                else 0
                            )
                            pbar.set_postfix_str(f"{speed_mbps:.2f} MB/s")
                        else:
                            # Segment failed to download
                            logger.error(f"Failed to download segment: {segment_name}")
                            failed_segments.append(segment_name)
                            pbar.update(1)  # Still update progress bar
                    except Exception as e:
                        logger.error(f"Exception downloading segment {segment_name}: {e}")
                        logger.error(f"Segment URL: {seg_url}")
                        failed_segments.append(segment_name)
                        pbar.update(1)  # Still update progress bar
                
                if failed_segments:
                    logger.warning(f"Failed to download {len(failed_segments)} segments: {', '.join(failed_segments[:5])}")
                    if len(failed_segments) > 5:
                        logger.warning(f"... and {len(failed_segments) - 5} more segments")
                    logger.info("These segments will be retried on next download attempt.")
                    return False  # Return False if any segments failed

        return True

    def compile_video(
        self,
        segment_dir: str,
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Compiles downloaded segments into a single mp4 file using ffmpeg.

        It creates a file list for ffmpeg's concat demuxer and then runs the
        ffmpeg command, capturing its progress to provide feedback.

        Args:
            segment_dir: The directory containing the downloaded .ts segments.
            output_path: The final path for the compiled .mp4 video.
            progress_callback: An optional function to call with progress (0-100).

        Returns:
            True on successful compilation, False otherwise.
        """
        playlist_path = os.path.join(segment_dir, "playlist.m3u8")
        file_list_path = os.path.join(segment_dir, "file.list")

        playlist_details = self.get_playlist_details(playlist_path)
        total_duration = (
            playlist_details.get("duration", 0.0) if playlist_details else 0.0
        )

        # Create the file list for ffmpeg
        with open(file_list_path, "w", encoding="utf-8") as f_out:
            if playlist_details:
                for segment_url in playlist_details.get("segments", []):
                    segment_name = os.path.basename(urlparse(segment_url).path)
                    f_out.write(f"file '{segment_name}'\n")

        # Resolve ffmpeg binary path (allow override via FFmpeg environment variable)
        ffmpeg_bin = os.environ.get("FFMPEG") or _shutil.which("ffmpeg")
        if not ffmpeg_bin:
            logger.error(
                "ffmpeg not found in PATH and FFMPEG env var not set. Cannot compile video."
            )
            return False

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file_list_path,
            "-c",
            "copy",
            output_path,
            "-progress",
            "pipe:1",
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        # Parse ffmpeg's stdout to calculate progress
        for line in iter(process.stdout.readline, ""):
            if "time=" in line and total_duration > 0 and progress_callback:
                match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                if match:
                    h, m, s, ms = map(int, match.groups())
                    current_time = h * 3600 + m * 60 + s + ms / 100
                    percent = int((current_time / total_duration) * 100)
                    progress_callback(min(percent, 100))

        process.wait()

        if process.returncode == 0:
            # Clean up the temporary segment directory
            shutil.rmtree(segment_dir)
            if progress_callback:
                progress_callback(100)  # Ensure it finishes at 100%
            return True
        else:
            logger.error(
                f"Failed to compile video. FFmpeg exited with code {process.returncode}."
            )
            # Optionally, print ffmpeg's output for debugging
            # print(process.stdout.read())
            return False
