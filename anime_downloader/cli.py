"""
Command-line interface for the AnimePahe Downloader.

This module provides the main command-line interface for the application.
It handles argument parsing, user interaction, and orchestrates the download
process.
"""

import argparse
import datetime
import json
import subprocess
import os
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Set
from tqdm import tqdm
from pyfzf.pyfzf import FzfPrompt
import questionary
from concurrent.futures import ThreadPoolExecutor, as_completed

# from plyer import notification
from . import config
from . import config_manager
from .api import AnimePaheAPI
from .downloader import Downloader
from .models import Anime, Episode
from .helper import sanitize_filename
from .logger import logger


def get_anime_dir(anime_name: str, download_dir: str) -> str:
    """
    Constructs the download path for a given anime.

    Args:
        anime_name: The name of the anime.
        download_dir: The root directory for downloads.

    Returns:
        The full path to the anime's download directory.
    """
    return os.path.join(download_dir, sanitize_filename(anime_name))


def get_episode_dir(anime_name: str, episode_number: int, download_dir: str) -> str:
    """
    Constructs the path to the folder where episode segments are stored.

    Args:
        anime_name: The name of the anime.
        episode_number: The episode number.
        download_dir: The root directory for downloads.

    Returns:
        The full path to the temporary directory for an episode.
    """
    return os.path.join(get_anime_dir(anime_name, download_dir), str(episode_number))


def get_video_path(anime_name: str, episode_number: int, download_dir: str) -> str:
    """
    Constructs the full path for the final episode video file.

    Args:
        anime_name: The name of the anime.
        episode_number: The episode number.
        download_dir: The root directory for downloads.

    Returns:
        The full path for the final .mp4 video file.
    """
    filename = f"{sanitize_filename(anime_name)} Episode {episode_number}.mp4"
    return os.path.join(get_anime_dir(anime_name, download_dir), filename)


def check_dependencies():
    """
    Checks if required command-line tools (ffmpeg, fzf, node) are installed.

    Exits the application if a dependency is not found.
    """
    if shutil.which("ffmpeg") is None:
        logger.critical("ffmpeg is not installed or not in your PATH.")
        sys.exit(1)
    if shutil.which("fzf") is None:
        logger.critical("fzf is not installed or not in your PATH.")
        sys.exit(1)
    if shutil.which("node") is None:
        logger.critical("node is not installed or not in your PATH.")
        sys.exit(1)


def choose_anime(api: AnimePaheAPI, query: str) -> Optional[Dict[str, str]]:
    """
    Prompts the user to select an anime from a list of search results using fzf.

    Args:
        api: An instance of the AnimePaheAPI.
        query: The user's search query.

    Returns:
        A dictionary containing the selected anime's 'title' and 'session' (slug),
        or None if no anime is selected.
    """
    results = api.search(query)
    if not results:
        logger.warning("No anime found for your query.")
        return None

    fzf = FzfPrompt()
    # Format for fzf: "Title"
    # We store slug and title in a dict for easy retrieval
    titles = [r["title"] for r in results]
    selection = fzf.prompt(titles)

    if selection:
        selected_title = selection[0]
        for r in results:
            if r["title"] == selected_title:
                return r
    return None


def parse_episode_selection(selection_str: str, max_episode: int) -> List[int]:
    """
    Parses a user's episode selection string, which can include ranges.

    Args:
        selection_str: The string input from the user (e.g., "1, 3, 5-10").
        max_episode: The highest available episode number to validate against.

    Returns:
        A sorted list of unique, valid episode numbers.
    """
    selected_numbers = set()
    parts = selection_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start_str, end_str = part.split('-')
                start = int(start_str.strip())
                end = int(end_str.strip())
                if start > end:
                    start, end = end, start  # Allow reverse ranges like 10-5
                for i in range(start, end + 1):
                    if i <= max_episode:
                        selected_numbers.add(i)
                    else:
                        logger.warning(f"Episode {i} is not available. Skipping.")
            except ValueError:
                logger.warning(f"Invalid range format: '{part}'. Skipping.")
                continue
        else:
            try:
                num = int(part)
                if num <= max_episode:
                    selected_numbers.add(num)
                else:
                    logger.warning(f"Episode {num} is not available. Skipping.")
            except ValueError:
                logger.warning(f"Invalid episode number: '{part}'. Skipping.")
                continue
    return sorted(list(selected_numbers))


def select_episodes(anime: Anime) -> List[int]:
    """
    Prompts the user to select which episodes to download using questionary.

    Args:
        anime: The Anime object for which to select episodes.

    Returns:
        A sorted list of selected episode numbers.
    """
    if not anime.episodes:
        logger.warning("No episodes found for this anime.")
        return []

    ep_numbers = [ep.number for ep in anime.episodes]
    min_ep, max_ep = min(ep_numbers), max(ep_numbers)

    downloaded_eps = {ep.number for ep in anime.episodes if ep.is_downloaded}

    logger.info(f"Episodes available: {min_ep}-{max_ep}")
    if downloaded_eps:
        logger.info(f"Already downloaded: {', '.join(map(str, sorted(list(downloaded_eps))))}")

    selection_str = questionary.text(
        "Enter episodes to download (e.g., 1, 3, 5-10):",
        validate=lambda text: True if text.strip() else "Please enter a selection.",
    ).ask()

    if not selection_str:
        return []

    return parse_episode_selection(selection_str, max_ep)


def download_single_episode(
    api: AnimePaheAPI,
    downloader: Downloader,
    details: Dict[str, Any],
    args: argparse.Namespace,
    app_config: Dict[str, Any],
):
    """
    Handles the download and compilation of a single episode.

    Args:
        api: An instance of the AnimePaheAPI.
        downloader: An instance of the Downloader.
        details: A dictionary containing anime and episode information.
        args: The parsed command-line arguments.
        app_config: The application configuration dictionary.
    """
    anime_name = details["name"]
    anime_slug = details["slug"]
    ep_num = details["episode_num"]
    ep_session = details["episode_session"]
    download_dir = app_config["download_directory"]

    logger.info(f"Starting download for Episode {ep_num}...")

    # 1. Get the stream URL from the /play page
    stream_url = api.get_stream_url(anime_slug, ep_session, args.quality, args.audio)
    if not stream_url:
        logger.error(f"Could not find a matching stream for episode {ep_num}.")
        return

    # 2. Get the m3u8 playlist URL from the stream page
    playlist_url = api.get_playlist_url(stream_url)
    if not playlist_url:
        logger.error(f"Could not get playlist link for episode {ep_num}.")
        return

    # 3. Download the playlist and video segments
    episode_dir = get_episode_dir(anime_name, ep_num, download_dir)
    playlist_path = downloader.fetch_playlist(playlist_url, episode_dir)
    if not playlist_path:
        return  # Error message is logged in the downloader

    # 4. Download segments from the playlist
    if downloader.download_from_playlist_cli(playlist_path, args.threads):
        # 5. Compile the downloaded segments into a single video file
        output_path = get_video_path(anime_name, ep_num, download_dir)
        # For CLI, we can create a simple tqdm progress bar for compilation
        with tqdm(total=100, desc=f"Compiling Ep. {ep_num}", unit="%", leave=False) as pbar:

            def update_pbar(percent):
                pbar.n = int(percent)
                pbar.refresh()

            downloader.compile_video(
                episode_dir, output_path, progress_callback=update_pbar
            )

        # 6. Send a desktop notification upon completion
        # try:
        #     notification.notify(
        #         title="Animepahe-dl",
        #         message=f"Finished downloading Ep {ep_num} of {anime_name}",
        #         app_name="Animepahe Downloader",
        #     )
        # except Exception as e:
        #     logger.warning(f"Failed to send notification: {e}")


def run_update_check(
    api: AnimePaheAPI,
    downloader: Downloader,
    args: argparse.Namespace,
    app_config: Dict[str, Any],
):
    """
    Checks for new episodes of anime in the user's list and downloads them.
    """
    logger.info("Checking for updates...")
    try:
        with open(config.MY_ANIME_LIST_FILE, "r", encoding="utf-8") as f:
            my_anime_list = [line.strip() for line in f]
    except FileNotFoundError:
        logger.warning("Your anime list is empty. Add some anime first.")
        return

    new_episodes = api.check_for_updates()
    if not new_episodes:
        logger.info("No new episodes found.")
        return

    download_queue = []
    for episode_data in new_episodes:
        if episode_data["anime_title"] in my_anime_list:
            anime_name = episode_data["anime_title"]
            anime_slug = episode_data["anime_session"]
            ep_num = int(episode_data["episode"])
            ep_session = episode_data["session"]

            # Check if already downloaded
            video_path = get_video_path(
                anime_name, ep_num, app_config["download_directory"]
            )
            if not os.path.exists(video_path):
                logger.success(f"Found new episode: {anime_name} - Episode {ep_num}")
                download_queue.append(
                    {
                        "name": anime_name,
                        "slug": anime_slug,
                        "episode_num": ep_num,
                        "episode_session": ep_session,
                    }
                )

    if not download_queue:
        logger.info("All new episodes are already downloaded.")
        return

    logger.info(f"Found {len(download_queue)} new episodes to download.")
    for item in download_queue:
        download_single_episode(api, downloader, item, args, app_config)

    logger.success("Update check finished!")


def manage_my_list():
    """
    Allows the user to add or remove anime from their personal list using fzf.
    """
    try:
        with open(config.MY_ANIME_LIST_FILE, "r+", encoding="utf-8") as f:
            current_list = [line.strip() for line in f]
            fzf = FzfPrompt()
            # Use fzf to select items to remove
            to_remove = fzf.prompt(
                current_list, "--multi --prompt 'Select anime to REMOVE > '"
            )

            if to_remove:
                updated_list = [item for item in current_list if item not in to_remove]
                f.seek(0)
                f.truncate()
                f.write("\n".join(updated_list) + "\n")
                logger.info(f"Removed {len(to_remove)} anime from your list.")

    except FileNotFoundError:
        logger.warning("Your anime list is empty. Nothing to manage.")


def main():
    """Main function to handle command-line arguments and orchestrate the download process."""
    # Ensure all external dependencies are met before starting
    check_dependencies()
    # Load user configuration from file
    app_config = config_manager.load_config()

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="A script to download anime from Animepahe.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-n", "--name", type=str, default="", help="Name of the anime to search for."
    )
    parser.add_argument(
        "-e",
        "--episodes",
        type=str,  # Changed to string to accept ranges
        default="",
        help="List or range of episode numbers to download (e.g., 1,2,5 or 5-10).",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=str,
        default=app_config.get("quality", "best"),
        help="Desired quality (e.g., 720, 1080, or 'best' for max resolution).",
    )
    parser.add_argument(
        "-a",
        "--audio",
        type=str,
        default=app_config.get("audio", "jpn"),
        help="Desired audio (eng or jpn).",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=app_config.get("threads", 50),
        help="Number of download threads for segments.",
    )
    parser.add_argument(
        "-c",
        "--concurrent-downloads",
        type=int,
        default=app_config.get("concurrent_downloads", 2),
        help="Number of episodes to download concurrently.",
    )
    parser.add_argument(
        "--updates",
        action="store_true",
        help="Check for new episodes of anime in your list.",
    )
    parser.add_argument(
        "--manage", action="store_true", help="Manage your personal anime list."
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run update check once and exit (for cron jobs).",
    )

    args = parser.parse_args()
    api = AnimePaheAPI()
    downloader = Downloader(api)

    # --- Auto-update Cache ---
    api.download_anime_list_cache()
    logger.info("Cache update complete.")

    # --- Mode Selection ---
    if args.updates:
        # Run in a loop to periodically check for updates
        while True:
            run_update_check(api, downloader, args, app_config)
            if args.run_once:
                break
            logger.info(
                f"Waiting for {config.UPDATE_CHECK_INTERVAL_MINUTES} minutes before next check..."
            )
            time.sleep(config.UPDATE_CHECK_INTERVAL_MINUTES * 60)
    elif args.manage:
        manage_my_list()
    else:
        # --- Default Mode: Search and Download ---
        # 1. Search for an anime
        selected_anime = choose_anime(api, args.name)
        if not selected_anime:
            return

        anime_name = selected_anime["title"]
        anime_slug = selected_anime["session"]

        # 2. Add the selected anime to the user's personal list
        try:
            with open(config.MY_ANIME_LIST_FILE, "a+", encoding="utf-8") as f:
                f.seek(0)
                if anime_name not in f.read():
                    f.write(f"{anime_name}\n")
        except IOError as e:
            logger.warning(f"Could not write to anime list file: {e}")

        # 3. Fetch all episode data for the selected anime
        episode_data = api.fetch_episode_data(anime_name, anime_slug)
        if not episode_data:
            logger.error("Could not fetch any episodes for this anime.")
            return

        download_dir = app_config["download_directory"]
        os.makedirs(get_anime_dir(anime_name, download_dir), exist_ok=True)

        # 4. Create an Anime object and populate it with episodes
        anime = Anime(name=anime_name, slug=anime_slug)
        max_ep = 0
        for ep_data in episode_data:
            ep_num = int(ep_data["episode"])
            if ep_num > max_ep:
                max_ep = ep_num
            # Check if the final video file already exists
            video_path = get_video_path(anime_name, ep_num, download_dir)
            anime.episodes.append(
                Episode(
                    number=ep_num,
                    session=ep_data["session"],
                    is_downloaded=os.path.exists(video_path),
                )
            )

        # 5. Select which episodes to download
        if not args.episodes:
            # If no specific episodes are provided via flags, prompt the user
            episodes_to_download = select_episodes(anime)
        else:
            # Otherwise, use the episodes from the command line
            episodes_to_download = parse_episode_selection(args.episodes, max_ep)

        if not episodes_to_download:
            logger.info("No episodes selected for download.")
            return

        logger.info(f"Selected Episodes: {', '.join(map(str, episodes_to_download))}")

        # 6. Download each selected episode concurrently
        with ThreadPoolExecutor(max_workers=args.concurrent_downloads) as executor:
            futures = []
            for ep_num in episodes_to_download:
                episode = anime.get_episode(ep_num)
                if not episode:
                    logger.warning(f"Episode {ep_num} not found for this anime.")
                    continue
                if episode.is_downloaded:
                    logger.info(f"Episode {ep_num} is already downloaded. Skipping.")
                    continue

                future = executor.submit(
                    download_single_episode,
                    api,
                    downloader,
                    {
                        "name": anime.name,
                        "slug": anime.slug,
                        "episode_num": episode.number,
                        "episode_session": episode.session,
                    },
                    args,
                    app_config,
                )
                futures.append(future)

            with tqdm(total=len(futures), desc="Overall Progress") as pbar:
                for future in as_completed(futures):
                    try:
                        future.result()  # Wait for the download to complete
                    except Exception as e:
                        logger.error(f"An episode download failed: {e}")
                    pbar.update(1)

        logger.success("All selected downloads are finished!")
