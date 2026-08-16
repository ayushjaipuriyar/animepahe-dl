"""
Background workers for handling long-running tasks in the GUI.

This module provides `QThread` subclasses that perform tasks like fetching data
from the API and downloading files in the background. This prevents the GUI
from freezing and allows for progress reporting.
"""

import os
import time
from typing import Any, Dict, List

from plyer import notification
from PyQt6.QtCore import QThread, pyqtSignal

from ..api import AnimePaheAPI, Downloader
from ..cli.commands import get_episode_dir, get_video_path
from ..models import Anime, Episode
from ..utils import config_manager


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
                video_path = get_video_path(anime_name, ep_num, download_dir)
                episode = Episode(number=ep_num, session=ep_data["session"])
                # Set download status based on file existence
                if os.path.exists(video_path):
                    episode.mark_as_downloaded(video_path)
                anime.episodes.append(episode)
            self.finished.emit(anime)
        except Exception as e:
            print(f"Error in EpisodeWorker: {e}")
            import traceback

            print(f"Full traceback: {traceback.format_exc()}")
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
                    self.log.emit(f"Error: Could not get playlist link for Ep {episode.number}")
                    continue

                # --- Step 2: Download Playlist and Segments ---
                episode_dir = get_episode_dir(
                    self.anime.name,
                    episode.number,
                    self.app_config["download_directory"],
                )
                playlist_path = self.downloader.fetch_playlist(playlist_url, episode_dir)
                if not playlist_path:
                    continue

                playlist_details = self.downloader.get_playlist_details(playlist_path)
                if not playlist_details:
                    self.log.emit(f"Error: Could not parse playlist for Ep {episode.number}")
                    continue

                key_response = self.api._request(playlist_details["key_url"])
                if not key_response:
                    self.log.emit(
                        f"Error: Failed to download decryption key for Ep {episode.number}"
                    )
                    continue
                key = key_response.data

                total_segments = len(playlist_details["segments"])
                self.log.emit(
                    f"Downloading {total_segments} segments for Ep {episode.number}..."
                )
                seg_start = time.time()

                def seg_progress(done, total, total_bytes):
                    elapsed = time.time() - seg_start
                    speed = (total_bytes / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    self.progress_update.emit(
                        done,
                        total,
                        f"({done}/{total}) {total_bytes / (1024*1024):.2f} MB @ {speed:.2f} MB/s",
                    )

                ok, failed = self.downloader.download_segments(
                    playlist_details,
                    key,
                    episode_dir,
                    self.app_config["threads"],
                    seg_progress,
                )
                if not ok:
                    self.log.emit(
                        f"Error: {len(failed)} segment(s) for Ep {episode.number} failed after "
                        f"retries. Not compiling; partial download kept for resume."
                    )
                    continue

                # --- Step 3: Compile Video ---
                self.log.emit(f"Compiling Episode {episode.number}...")
                output_path = get_video_path(
                    self.anime.name,
                    episode.number,
                    self.app_config["download_directory"],
                )

                # Use a lambda to add episode context to the progress callback
                progress_callback = lambda p: self.on_compilation_progress(p, episode.number)

                if not self.downloader.compile_video(episode_dir, output_path, progress_callback):
                    self.log.emit(
                        f"Error: Episode {episode.number} did not compile completely "
                        f"(incomplete or truncated). Not marking as downloaded."
                    )
                    continue
                self.log.emit(f"Finished processing Episode {episode.number}")

                # Send desktop notification
                try:
                    notification.notify(
                        title="Animepahe-dl",
                        message=f"Finished downloading {self.anime.name} Episode {episode.number}",
                        app_name="Animepahe Downloader",
                        timeout=10,
                    )
                except Exception as e:
                    print(f"Failed to send notification: {e}")

            except Exception as e:
                self.log.emit(f"An error occurred while downloading Ep {episode.number}: {e}")
                print(f"Error downloading episode {episode.number}: {e}")
                import traceback

                print(f"Full traceback: {traceback.format_exc()}")
                continue  # Move to the next episode

        self.finished.emit()

    def on_compilation_progress(self, percent: int, episode_number: int):
        """
        Relays compilation progress to the GUI, including the episode number.

        Args:
            percent: The compilation progress percentage (0-100).
            episode_number: The number of the episode being compiled.
        """
        message = f"Compiling Ep {episode_number}... {percent}%"
        self.progress_update.emit(percent, 100, message)


class MultiAnimeDownloadWorker(QThread):
    """
    A QThread worker for downloading episodes from multiple anime.

    This worker fetches episode data for each anime and downloads all available
    episodes that haven't been downloaded yet.

    Signals:
        progress_update (int, int, str): Emits (current, total, message) for progress.
        log (str): Emits a string message for logging in the status bar.
        finished (): Emitted when all downloads are complete.
    """

    progress_update = pyqtSignal(int, int, str)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        api: AnimePaheAPI,
        downloader: Downloader,
        anime_list: List[Dict[str, str]],
        app_config: Dict[str, Any],
    ):
        super().__init__()
        self.api = api
        self.downloader = downloader
        self.anime_list = anime_list
        self.app_config = app_config

    def run(self):
        """Fetches episodes for each anime and downloads them."""
        download_dir = self.app_config["download_directory"]
        all_episodes_to_download = []

        # Step 1: Fetch episode data for all selected anime
        self.log.emit(f"Fetching episode data for {len(self.anime_list)} anime...")

        for anime_data in self.anime_list:
            try:
                anime_name = anime_data["title"]
                anime_slug = anime_data["session"]

                self.log.emit(f"Fetching episodes for {anime_name}...")
                episode_data = self.api.fetch_episode_data(anime_name, anime_slug)

                if not episode_data:
                    self.log.emit(f"No episodes found for {anime_name}")
                    continue

                anime = Anime(name=anime_name, slug=anime_slug)
                for ep_data in episode_data:
                    ep_num = int(ep_data["episode"])
                    video_path = get_video_path(anime_name, ep_num, download_dir)
                    episode = Episode(number=ep_num, session=ep_data["session"])
                    # Set download status based on file existence
                    if os.path.exists(video_path):
                        episode.mark_as_downloaded(video_path)
                    anime.episodes.append(episode)

                    # Queue non-downloaded episodes
                    if not episode.is_downloaded:
                        all_episodes_to_download.append((anime, episode))

                self.log.emit(
                    f"Found {len([e for e in anime.episodes if not e.is_downloaded])} episodes to download for {anime_name}"
                )

            except Exception as e:
                self.log.emit(f"Error fetching episodes for {anime_data['title']}: {e}")
                continue

        if not all_episodes_to_download:
            self.log.emit("No new episodes to download.")
            self.finished.emit()
            return

        # Step 2: Download all queued episodes
        total_episodes = len(all_episodes_to_download)
        self.log.emit(f"Starting download of {total_episodes} episodes...")

        for idx, (anime, episode) in enumerate(all_episodes_to_download, 1):
            try:
                self.log.emit(
                    f"[{idx}/{total_episodes}] Downloading {anime.name} - Episode {episode.number}..."
                )

                # Get stream and playlist URLs
                stream_url = self.api.get_stream_url(
                    anime.slug,
                    episode.session,
                    self.app_config["quality"],
                    self.app_config["audio"],
                )
                if not stream_url:
                    self.log.emit(
                        f"Error: Could not find stream for {anime.name} Ep {episode.number}"
                    )
                    continue

                playlist_url = self.api.get_playlist_url(stream_url)
                if not playlist_url:
                    self.log.emit(
                        f"Error: Could not get playlist for {anime.name} Ep {episode.number}"
                    )
                    continue

                # Download playlist and segments
                episode_dir = get_episode_dir(anime.name, episode.number, download_dir)
                playlist_path = self.downloader.fetch_playlist(playlist_url, episode_dir)
                if not playlist_path:
                    continue

                playlist_details = self.downloader.get_playlist_details(playlist_path)
                if not playlist_details:
                    self.log.emit(
                        f"Error: Could not parse playlist for {anime.name} Ep {episode.number}"
                    )
                    continue

                key_response = self.api._request(playlist_details["key_url"])
                if not key_response:
                    self.log.emit(
                        f"Error: Failed to get decryption key for {anime.name} Ep {episode.number}"
                    )
                    continue
                key = key_response.data

                total_segments = len(playlist_details["segments"])
                self.log.emit(f"Downloading {total_segments} segments...")
                ok, failed = self.downloader.download_segments(
                    playlist_details,
                    key,
                    episode_dir,
                    self.app_config["threads"],
                    lambda done, total, _b: self.progress_update.emit(
                        idx, total_episodes, f"Ep {episode.number}: segment {done}/{total}"
                    ),
                )
                if not ok:
                    self.log.emit(
                        f"Error: {len(failed)} segment(s) failed for {anime.name} "
                        f"Ep {episode.number}; kept for resume, not compiling."
                    )
                    continue

                # Compile video
                self.log.emit(f"Compiling {anime.name} Episode {episode.number}...")
                output_path = get_video_path(anime.name, episode.number, download_dir)
                if not self.downloader.compile_video(episode_dir, output_path, lambda p: None):
                    self.log.emit(
                        f"Error: {anime.name} Ep {episode.number} did not compile completely "
                        f"(incomplete or truncated). Not marking as downloaded."
                    )
                    continue

                self.log.emit(f"Completed {anime.name} Episode {episode.number}")
                self.progress_update.emit(
                    idx, total_episodes, f"Completed {idx}/{total_episodes} episodes"
                )

            except Exception as e:
                self.log.emit(f"Error downloading {anime.name} Ep {episode.number}: {e}")
                print(f"Error in MultiAnimeDownloadWorker: {e}")
                import traceback

                print(f"Full traceback: {traceback.format_exc()}")
                continue

        self.log.emit(f"Finished downloading {total_episodes} episodes!")
        self.finished.emit()


class PlaybackWorker(QThread):
    """
    A QThread worker for playing episodes using external media players.

    This worker gets the m3u8 stream URLs and launches external media players
    to play the episodes directly without downloading.

    Signals:
        finished (): Emitted when playback session is complete.
        error (str): Emitted when an error occurs.
        episode_started (int, str): Emitted when an episode starts playing.
    """

    finished = pyqtSignal()
    error = pyqtSignal(str)
    episode_started = pyqtSignal(int, str)

    def __init__(
        self,
        api: AnimePaheAPI,
        anime_name: str,
        anime_slug: str,
        episodes: List[tuple],  # List of (episode_num, episode_session) tuples
        quality: str,
        audio: str,
        media_player: str,
    ):
        super().__init__()
        self.api = api
        self.anime_name = anime_name
        self.anime_slug = anime_slug
        self.episodes = episodes
        self.quality = quality
        self.audio = audio
        self.media_player = media_player

    def run(self):
        """Plays each episode in sequence using the external media player."""
        import subprocess

        try:
            for episode_num, episode_session in self.episodes:
                self.episode_started.emit(episode_num, self.anime_name)

                # Get stream URL
                stream_url = self.api.get_stream_url(
                    self.anime_slug, episode_session, self.quality, self.audio
                )
                if not stream_url:
                    self.error.emit(f"Could not find stream for Episode {episode_num}")
                    continue

                # Get playlist URL
                playlist_url = self.api.get_playlist_url(stream_url)
                if not playlist_url:
                    self.error.emit(f"Could not get playlist for Episode {episode_num}")
                    continue

                # Launch media player
                try:
                    if self.media_player == "mpv":
                        cmd = [
                            self.media_player,
                            "--title",
                            f"{self.anime_name} - Episode {episode_num}",
                            "--force-window=immediate",
                            playlist_url,
                        ]
                    elif self.media_player == "vlc":
                        cmd = [
                            self.media_player,
                            "--intf",
                            "qt",
                            "--meta-title",
                            f"{self.anime_name} - Episode {episode_num}",
                            playlist_url,
                        ]
                    elif self.media_player == "ffplay":
                        cmd = [
                            self.media_player,
                            "-window_title",
                            f"{self.anime_name} - Episode {episode_num}",
                            "-autoexit",
                            playlist_url,
                        ]
                    elif self.media_player == "mplayer":
                        cmd = [
                            self.media_player,
                            "-title",
                            f"{self.anime_name} - Episode {episode_num}",
                            playlist_url,
                        ]
                    else:
                        # Generic fallback
                        cmd = [self.media_player, playlist_url]

                    # Launch the player
                    process = subprocess.Popen(
                        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )

                    # For players that block (like ffplay), wait for completion
                    # For others, just launch and continue
                    if self.media_player in ["ffplay"]:
                        process.wait()

                except subprocess.SubprocessError as e:
                    self.error.emit(f"Failed to launch {self.media_player}: {str(e)}")
                    continue
                except Exception as e:
                    self.error.emit(f"Unexpected error playing Episode {episode_num}: {str(e)}")
                    continue

            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Playback worker error: {str(e)}")
