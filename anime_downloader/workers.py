"""
Background workers for handling long-running tasks in the GUI.

This module provides `QThread` subclasses that perform tasks like fetching data
from the API and downloading files in the background. This prevents the GUI
from freezing and allows for progress reporting.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from PyQt6.QtCore import QThread, pyqtSignal
from typing import List, Dict, Any

from .api import AnimePaheAPI
from .downloader import Downloader
from .models import Anime, Episode
from . import config_manager
from . import cli


class UpdateCacheWorker(QThread):
    """Worker to refresh the anime list cache.

    Emits:
        finished(int): Count of entries written.
            > 0  => success with that many entries
            0    => empty parse (treat as failure/alert)
           -1    => network / write failure
    """

    finished = pyqtSignal(int)

    def __init__(self, api: AnimePaheAPI):
        super().__init__()
        self.api = api

    def run(self):
        """Run cache update and emit entry count."""
        try:
            count = self.api.download_anime_list_cache()
            self.finished.emit(count)
        except Exception as e:
            print(f"Error in UpdateCacheWorker: {e}")
            self.finished.emit(-1)


class EpisodeWorker(QThread):
    """
    A QThread worker for fetching the episode list for a specific anime.

    Signals:
        finished (object): Emitted when the episode list has been fetched.
                           The object is the `Anime` instance with its episodes.
    """

    finished = pyqtSignal(object)

    def __init__(self, api: AnimePaheAPI, anime_data: Dict[str, str]):
        super().__init__()
        self.api = api
        self.anime_data = anime_data

    def run(self):
        """Fetches episode data, creates an Anime object, and emits it."""
        try:
            anime_name = self.anime_data["title"]
            anime_slug = self.anime_data["session"]
            episode_data = self.api.fetch_episode_data(anime_name, anime_slug)

            app_config = config_manager.load_config()
            download_dir = app_config["download_directory"]

            anime = Anime(name=anime_name, slug=anime_slug)
            for ep_data in episode_data:
                ep_num = int(ep_data["episode"])
                # Check if the final video file already exists
                video_path = cli.get_video_path(anime_name, ep_num, download_dir)
                anime.episodes.append(
                    Episode(
                        number=ep_num,
                        session=ep_data["session"],
                        is_downloaded=cli.os.path.exists(video_path),
                    )
                )
            self.finished.emit(anime)
        except Exception as e:
            print(f"Error in EpisodeWorker: {e}")
            self.finished.emit(None)  # Emit None on failure


class DownloadWorker(QThread):
    """
    A QThread worker for downloading and compiling episodes.

    This worker manages a thread pool for downloading segments in parallel
    and emits signals to update the GUI with progress.

    Signals:
        progress_update (int, int, str): Emits (current, total, message) for progress.
        log (str): Emits a string message for logging in the status bar.
        finished (): Emitted when all downloads in the queue are complete.
    """

    progress_update = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        api: AnimePaheAPI,
        downloader: Downloader,
        anime: Anime,
        episodes: List[Episode],
        app_config: Dict[str, Any],
    ):
        super().__init__()
        self.api = api
        self.downloader = downloader
        self.anime = anime
        self.episodes = episodes
        self.app_config = app_config

    def run(self):
        """Iterates through the episode queue and handles the download for each."""
        for i, episode in enumerate(self.episodes):
            try:
                self.log.emit(
                    f"Starting Ep {episode.number}/{self.episodes[-1].number} of {self.anime.name}..."
                )

                # --- Step 1: Get Stream and Playlist URLs ---
                stream_url = self.api.get_stream_url(
                    self.anime.slug,
                    episode.session,
                    self.app_config["quality"],
                    self.app_config["audio"],
                )
                if not stream_url:
                    self.log.emit(
                        f"Error: Could not find a matching stream for Ep {episode.number}"
                    )
                    continue

                playlist_url = self.api.get_playlist_url(stream_url)
                if not playlist_url:
                    self.log.emit(
                        f"Error: Could not get playlist link for Ep {episode.number}"
                    )
                    continue

                # --- Step 2: Download Playlist and Segments ---
                episode_dir = cli.get_episode_dir(
                    self.anime.name,
                    episode.number,
                    self.app_config["download_directory"],
                )
                playlist_path = self.downloader.fetch_playlist(
                    playlist_url, episode_dir
                )
                if not playlist_path:
                    continue

                playlist_details = self.downloader.get_playlist_details(playlist_path)
                if not playlist_details:
                    self.log.emit(
                        f"Error: Could not parse playlist for Ep {episode.number}"
                    )
                    continue

                key_response = self.api._request(playlist_details["key_url"])
                if not key_response:
                    self.log.emit(
                        f"Error: Failed to download decryption key for Ep {episode.number}"
                    )
                    continue
                key = key_response.data

                segments = playlist_details["segments"]
                segments_to_download = [
                    s
                    for s in segments
                    if not cli.os.path.exists(
                        cli.os.path.join(
                            episode_dir, cli.os.path.basename(urlparse(s).path)
                        )
                    )
                ]

                if not segments_to_download:
                    self.log.emit(
                        f"Segments for Ep {episode.number} already downloaded."
                    )
                else:
                    self.log.emit(
                        f"Downloading {len(segments_to_download)} segments for Ep {episode.number}..."
                    )
                    self._run_segment_downloads(
                        segments_to_download, playlist_details, key, episode_dir
                    )

                # --- Step 3: Compile Video ---
                self.log.emit(f"Compiling Episode {episode.number}...")
                output_path = cli.get_video_path(
                    self.anime.name,
                    episode.number,
                    self.app_config["download_directory"],
                )

                # Use a lambda to add episode context to the progress callback
                progress_callback = lambda p: self.on_compilation_progress(
                    p, episode.number
                )

                self.downloader.compile_video(
                    episode_dir, output_path, progress_callback
                )
                self.log.emit(f"Finished processing Episode {episode.number}")

            except Exception as e:
                self.log.emit(
                    f"An error occurred while downloading Ep {episode.number}: {e}"
                )
                continue  # Move to the next episode

        self.finished.emit()

    def _run_segment_downloads(
        self, segments_to_download, playlist_details, key, episode_dir
    ):
        """Manages the thread pool for downloading segments for a single episode."""
        total_segments = len(segments_to_download)
        segments_done = 0
        total_bytes = 0
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.app_config["threads"]) as executor:
            futures = []
            for seg_url in segments_to_download:
                original_index = playlist_details["segments"].index(seg_url)
                segment_index = playlist_details["media_sequence"] + original_index
                iv = segment_index.to_bytes(16, byteorder="big")
                segment_name = cli.os.path.basename(urlparse(seg_url).path)
                output_path = cli.os.path.join(episode_dir, segment_name)
                futures.append(
                    executor.submit(
                        self.downloader.download_segment, seg_url, key, iv, output_path
                    )
                )

            for future in as_completed(futures):
                bytes_downloaded = future.result()
                if bytes_downloaded > 0:
                    segments_done += 1
                    total_bytes += bytes_downloaded
                    elapsed_time = time.time() - start_time
                    speed_mbps = (
                        (total_bytes / (1024 * 1024)) / elapsed_time
                        if elapsed_time > 0
                        else 0
                    )
                    message = f"({segments_done}/{total_segments}) {total_bytes / (1024*1024):.2f} MB @ {speed_mbps:.2f} MB/s"
                    self.progress_update.emit(segments_done, total_segments, message)

    def on_compilation_progress(self, percent: int, episode_number: int):
        """
        Relays compilation progress to the GUI, including the episode number.

        Args:
            percent: The compilation progress percentage (0-100).
            episode_number: The number of the episode being compiled.
        """
        message = f"Compiling Ep {episode_number}... {percent}%"
        self.progress_update.emit(percent, 100, message)
