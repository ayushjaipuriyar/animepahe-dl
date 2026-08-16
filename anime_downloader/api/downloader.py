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
import shutil as _shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional
from urllib.parse import urlparse

from Crypto.Cipher import AES
from tqdm import tqdm

from ..core.signal_handler import is_shutdown_requested
from ..utils import constants, logger
from .client import AnimePaheAPI


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

    def download_segment(self, url: str, key: bytes, iv: bytes, output_path: str) -> int:
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
        # Skip if already downloaded AND non-empty. A 0-byte file is a leftover
        # from a previously failed run — fall through and re-download it.
        if os.path.exists(output_path):
            try:
                existing_size = os.path.getsize(output_path)
            except OSError:
                existing_size = 0
            if existing_size > 0:
                logger.info(f"✓ Resuming: Segment already exists: {os.path.basename(output_path)}")
                return existing_size

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

        # AES-128-CBC ciphertext is always a whole number of 16-byte blocks. An
        # empty body or a non-block-aligned body means the transfer was truncated
        # or failed. The old code padded such bodies with NUL bytes and wrote the
        # result to disk, silently producing a corrupt segment that later made
        # ffmpeg stop mid-video. Treat it as a failure and write nothing so this
        # segment is retried instead of poisoning the merge.
        if bytes_downloaded == 0 or bytes_downloaded % 16 != 0:
            logger.error(
                f"Segment {segment_name} returned {bytes_downloaded} bytes "
                f"(empty or not 16-byte aligned) — treating as failed, not writing."
            )
            return 0

        # Decrypt the segment
        try:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted_data = cipher.decrypt(encrypted_data)
            with open(output_path, "wb") as f:
                f.write(decrypted_data)
            return bytes_downloaded
        except Exception as e:
            logger.error(f"Failed to decrypt or save segment {os.path.basename(output_path)}: {e}")
            # Remove any partial file so a retry re-downloads it cleanly.
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
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
            # Write atomically: a partially-written playlist from an interrupted
            # run must never be cached and silently reused as a short segment list.
            tmp_path = file_path + ".part"
            with open(tmp_path, "wb") as f:
                f.write(response.data)
            os.replace(tmp_path, file_path)
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

    def download_segments(
        self,
        playlist_details: dict,
        key: bytes,
        episode_dir: str,
        num_threads: int,
        progress_callback: Optional[Callable[[int, int, int], None]] = None,
        max_rounds: int = 3,
    ) -> tuple:
        """
        Downloads every segment in a playlist in parallel, retrying failures.

        This is the single shared segment-download routine used by both the CLI
        and the GUI. Previously each caller had its own copy of this loop, and the
        GUI's copy silently discarded failed segments — the core cause of
        "successful" downloads that were only a few minutes long.

        Args:
            playlist_details: Parsed playlist dict from get_playlist_details().
            key: The 16-byte AES decryption key.
            episode_dir: Directory to save the .ts segments into.
            num_threads: Number of parallel download workers.
            progress_callback: Optional fn(done, total, total_bytes) for progress.
            max_rounds: How many times to retry the set of still-failing segments.

        Returns:
            (success, failed_segment_names). success is True only if every segment
            was downloaded (and no shutdown was requested mid-way).
        """
        segments = playlist_details["segments"]
        media_sequence = playlist_details["media_sequence"]
        total = len(segments)

        def segment_path(seg_url: str) -> str:
            return os.path.join(episode_dir, os.path.basename(urlparse(seg_url).path))

        def is_present(seg_url: str) -> bool:
            p = segment_path(seg_url)
            return os.path.exists(p) and os.path.getsize(p) > 0

        pending = [s for s in segments if not is_present(s)]
        done = total - len(pending)
        total_bytes = 0
        if progress_callback:
            progress_callback(done, total, total_bytes)

        for round_num in range(1, max_rounds + 1):
            if not pending or is_shutdown_requested():
                break

            failed = []
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                future_to_seg = {}
                for seg_url in pending:
                    original_index = segments.index(seg_url)
                    iv = (media_sequence + original_index).to_bytes(16, byteorder="big")
                    future = executor.submit(
                        self.download_segment, seg_url, key, iv, segment_path(seg_url)
                    )
                    future_to_seg[future] = seg_url

                for future in as_completed(future_to_seg):
                    if is_shutdown_requested():
                        logger.info("Shutdown requested, stopping segment downloads.")
                        break
                    seg_url = future_to_seg[future]
                    try:
                        bytes_downloaded = future.result()
                    except Exception as e:
                        logger.error(f"Exception downloading {segment_path(seg_url)}: {e}")
                        bytes_downloaded = 0

                    if bytes_downloaded > 0:
                        done += 1
                        total_bytes += bytes_downloaded
                        if progress_callback:
                            progress_callback(done, total, total_bytes)
                    else:
                        failed.append(seg_url)

            pending = failed
            if pending and round_num < max_rounds and not is_shutdown_requested():
                logger.warning(
                    f"{len(pending)} segment(s) failed; retrying (round {round_num + 1}/{max_rounds})."
                )

        failed_names = [os.path.basename(urlparse(s).path) for s in pending]
        success = not failed_names and not is_shutdown_requested()
        return success, failed_names

    def download_from_playlist_cli(self, playlist_path: str, num_threads: int) -> bool:
        """
        Downloads all segments from a playlist for the CLI, with a tqdm progress bar.

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
        total = len(playlist_details["segments"])
        start_time = time.time()

        with tqdm(total=total, unit="seg", desc="Downloading") as pbar:

            def cb(done: int, _total: int, total_bytes: int) -> None:
                pbar.n = done
                elapsed = time.time() - start_time
                if elapsed > 0:
                    pbar.set_postfix_str(f"{(total_bytes / (1024 * 1024)) / elapsed:.2f} MB/s")
                pbar.refresh()

            success, failed_segments = self.download_segments(
                playlist_details, key, episode_dir, num_threads, cb
            )

        if not success:
            logger.warning(
                f"Failed to download {len(failed_segments)} segment(s): "
                f"{', '.join(failed_segments[:5])}"
                + (f" ... and {len(failed_segments) - 5} more" if len(failed_segments) > 5 else "")
            )
            logger.info("Incomplete segments are kept on disk and will be retried on next run.")
            return False

        return True

    def _probe_duration(self, path: str) -> Optional[float]:
        """Returns the media duration in seconds via ffprobe, or None if unavailable."""
        ffprobe_bin = os.environ.get("FFPROBE") or _shutil.which("ffprobe")
        if not ffprobe_bin or not os.path.exists(path):
            return None
        try:
            result = subprocess.run(
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return float(result.stdout.strip())
        except (ValueError, subprocess.SubprocessError, OSError):
            return None

    def compile_video(
        self,
        segment_dir: str,
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> bool:
        """
        Compiles downloaded segments into a single mp4 file using ffmpeg.

        Completeness is verified at both ends so a truncated result can never be
        reported as success:
          1. Every segment named in the playlist must exist on disk and be
             non-empty before the merge starts (a missing/empty segment is exactly
             what made ffmpeg stop a few minutes in).
          2. The decrypted MPEG-TS segments are binary-concatenated into one
             continuous stream and remuxed. This avoids the concat demuxer's
             per-file timestamp resets, which could silently truncate the output
             at the first discontinuity while still exiting 0.
          3. After the merge, the output duration is checked against the playlist's
             expected duration; a short result is rejected.
        On any failure the segments are left on disk so the next run can resume.

        Args:
            segment_dir: The directory containing the downloaded .ts segments.
            output_path: The final path for the compiled .mp4 video.
            progress_callback: An optional function to call with progress (0-100).

        Returns:
            True on successful, complete compilation, False otherwise.
        """
        playlist_path = os.path.join(segment_dir, "playlist.m3u8")

        playlist_details = self.get_playlist_details(playlist_path)
        if not playlist_details or not playlist_details.get("segments"):
            logger.error("Cannot compile: playlist details or segment list unavailable.")
            return False

        segments = playlist_details["segments"]
        total_duration = playlist_details.get("duration", 0.0)

        # 1. Verify every expected segment is present and non-empty.
        missing = [
            os.path.basename(urlparse(seg_url).path)
            for seg_url in segments
            if not (
                os.path.exists(os.path.join(segment_dir, os.path.basename(urlparse(seg_url).path)))
                and os.path.getsize(
                    os.path.join(segment_dir, os.path.basename(urlparse(seg_url).path))
                )
                > 0
            )
        ]
        if missing:
            logger.error(
                f"Cannot compile: {len(missing)} of {len(segments)} segments are "
                f"missing or empty (e.g. {', '.join(missing[:5])}). Keeping the partial "
                f"download so it can be resumed; not producing a truncated video."
            )
            return False

        # Resolve ffmpeg binary path (allow override via FFMPEG environment variable)
        ffmpeg_bin = os.environ.get("FFMPEG") or _shutil.which("ffmpeg")
        if not ffmpeg_bin:
            logger.error(
                "ffmpeg not found in PATH and FFMPEG env var not set. Cannot compile video."
            )
            return False

        # 2. Binary-concatenate the decrypted TS segments into one stream, then remux.
        combined_ts = os.path.join(segment_dir, "combined.ts")
        try:
            with open(combined_ts, "wb") as out_file:
                for seg_url in segments:
                    segment_name = os.path.basename(urlparse(seg_url).path)
                    with open(os.path.join(segment_dir, segment_name), "rb") as seg_file:
                        shutil.copyfileobj(seg_file, out_file)
        except OSError as e:
            logger.error(f"Failed to concatenate segments: {e}")
            return False

        cmd = [
            ffmpeg_bin,
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            combined_ts,
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
        if process.stdout is not None:
            for line in iter(process.stdout.readline, ""):
                if "time=" in line and total_duration > 0 and progress_callback:
                    match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", line)
                    if match:
                        h, m, s, ms = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s + ms / 100
                        percent = int((current_time / total_duration) * 100)
                        progress_callback(min(percent, 100))

        process.wait()

        try:
            os.remove(combined_ts)
        except OSError:
            pass

        if process.returncode != 0:
            logger.error(
                f"Failed to compile video. FFmpeg exited with code {process.returncode}. "
                f"Keeping segments for retry."
            )
            return False

        # 3. Reject a silently-truncated result (short output, ffmpeg exit 0).
        if total_duration > 0:
            actual_duration = self._probe_duration(output_path)
            if actual_duration is not None and actual_duration < total_duration * 0.98 - 2.0:
                logger.error(
                    f"Compiled video is {actual_duration:.0f}s but the playlist expects "
                    f"{total_duration:.0f}s — the output is truncated. Removing it and keeping "
                    f"segments; not marking the episode complete."
                )
                try:
                    os.remove(output_path)
                except OSError:
                    pass
                return False

        # Success: clean up the temporary segment directory.
        shutil.rmtree(segment_dir)
        if progress_callback:
            progress_callback(100)  # Ensure it finishes at 100%
        return True
