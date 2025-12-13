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
import signal
from typing import Any, Dict, List, Optional, Set
from tqdm import tqdm
from pyfzf.pyfzf import FzfPrompt
import questionary
from concurrent.futures import ThreadPoolExecutor, as_completed

from plyer import notification
from ..utils import constants, config_manager, helper
from ..api import AnimePaheAPI, Downloader
from ..models import Anime, Episode
from ..utils import logger
from ..core.signal_handler import setup_signal_handling, register_shutdown_callback, is_shutdown_requested


def get_anime_dir(anime_name: str, download_dir: str) -> str:
    """
    Constructs the download path for a given anime.

    Args:
        anime_name: The name of the anime.
        download_dir: The root directory for downloads.

    Returns:
        The full path to the anime's download directory.
    """
    return os.path.join(download_dir, helper.sanitize_filename(anime_name))


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
    filename = f"{helper.sanitize_filename(anime_name)} Episode {episode_number}.mp4"
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


def detect_media_player(preferred_player: str = "") -> Optional[str]:
    """
    Detects available media players on the system.
    
    Args:
        preferred_player: User's preferred media player.
        
    Returns:
        Path to the media player executable, or None if none found.
    """
    # List of media players in order of preference
    players = ["mpv", "vlc", "ffplay", "mplayer"]
    
    # If user specified a preferred player, try it first
    if preferred_player:
        if shutil.which(preferred_player):
            return preferred_player
        else:
            logger.warning(f"Specified player '{preferred_player}' not found. Trying alternatives...")
    
    # Try each player in order
    for player in players:
        if shutil.which(player):
            logger.info(f"Using media player: {player}")
            return player
    
    return None


def play_episode_stream(
    api: AnimePaheAPI,
    anime_name: str,
    anime_slug: str,
    ep_num: int,
    ep_session: str,
    quality: str,
    audio: str,
    player: str
):
    """
    Plays an episode directly using the m3u8 stream.
    
    Args:
        api: An instance of the AnimePaheAPI.
        anime_name: The name of the anime.
        anime_slug: The anime slug.
        ep_num: The episode number.
        ep_session: The episode session.
        quality: Desired video quality.
        audio: Desired audio language.
        player: Media player to use.
    """
    logger.info(f"Getting stream for {anime_name} Episode {ep_num}...")
    
    # Get the stream URL from the /play page
    stream_url = api.get_stream_url(anime_slug, ep_session, quality, audio)
    if not stream_url:
        logger.error(f"Could not find a matching stream for episode {ep_num}.")
        return False
    
    # Get the m3u8 playlist URL from the stream page
    playlist_url = api.get_playlist_url(stream_url)
    if not playlist_url:
        logger.error(f"Could not get playlist link for episode {ep_num}.")
        return False
    
    logger.info(f"Playing {anime_name} Episode {ep_num} with {player}...")
    logger.info(f"Stream URL: {playlist_url}")
    
    try:
        # Different players have different command line arguments
        if player == "mpv":
            cmd = [
                player,
                f"--title={anime_name} - Episode {ep_num}",
                f"--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                f"--referrer=https://animepahe.ru/",
                "--network-timeout=30",
                "--demuxer-max-bytes=50M",
                "--demuxer-max-back-bytes=25M",
                playlist_url
            ]
        elif player == "vlc":
            cmd = [player, "--intf", "dummy", "--play-and-exit", playlist_url]
        elif player == "ffplay":
            cmd = [player, "-window_title", f"{anime_name} - Episode {ep_num}", playlist_url]
        elif player == "mplayer":
            cmd = [player, "-title", f"{anime_name} - Episode {ep_num}", playlist_url]
        else:
            # Generic fallback
            cmd = [player, playlist_url]
        
        # Launch the media player
        # Don't suppress output initially to see if there are errors
        logger.info(f"Executing command: {' '.join(cmd)}")
        process = subprocess.Popen(cmd)
        logger.success(f"✓ Launched {player} for {anime_name} Episode {ep_num}")
        
        # Wait for the player to finish for all players to ensure proper playback
        try:
            process.wait()
            logger.info(f"Media player finished playing {anime_name} Episode {ep_num}")
        except KeyboardInterrupt:
            logger.info("Playback interrupted by user")
            process.terminate()
        
        return True
        
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to launch media player: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while playing episode: {e}")
        return False


def choose_anime(
    api: AnimePaheAPI, query: str, last_cache_count: Optional[int] = None, multi: bool = False
) -> Optional[List[Dict[str, str]]]:
    """
    Prompts the user to select one or more anime from a list of search results using fzf.

    Args:
        api: An instance of the AnimePaheAPI.
        query: The user's search query.
        last_cache_count: The count from the last cache update (for error messages).
        multi: If True, allows multiple selections using spacebar.

    Returns:
        A list of dictionaries, each containing 'title' and 'session' (slug),
        or None if no anime is selected.
    """
    results = api.search(query)
    if not results:
        if not query:
            # Distinguish empty cache vs query miss
            if last_cache_count == -1:
                logger.error(
                    "Anime cache update failed (network). Try adjusting base_url or checking connectivity."
                )
            elif last_cache_count == 0:
                logger.error(
                    "Anime cache is empty after update. The site structure may have changed or the base_url is incorrect.\n"
                    f"Current base_url: {constants.get_base_url()}\n"
                    "Suggestions: 1) Verify base_url with --set-base-url if supported / config.json 'base_url'. 2) Retry later."
                )
            else:
                logger.warning(
                    "Anime list cache appears empty. Run again with a query or update cache."
                )
        else:
            logger.warning("No anime found for your query.")
        return None

    fzf = FzfPrompt()
    # Format for fzf: "Title"
    # We store slug and title in a dict for easy retrieval
    titles = [r["title"] for r in results]
    
    # Use --multi flag if multi-selection is enabled
    fzf_options = "--multi --bind space:toggle" if multi else ""
    selection = fzf.prompt(titles, fzf_options) if fzf_options else fzf.prompt(titles)

    if selection:
        selected_anime = []
        for selected_title in selection:
            for r in results:
                if r["title"] == selected_title:
                    selected_anime.append(r)
                    break
        return selected_anime if selected_anime else None
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
    parts = selection_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-")
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
        logger.info(
            f"Already downloaded: {', '.join(map(str, sorted(list(downloaded_eps))))}"
        )

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

    # Check if final video already exists
    final_video_path = get_video_path(anime_name, ep_num, download_dir)
    if os.path.exists(final_video_path):
        logger.success(f"✓ Resuming: {anime_name} Episode {ep_num} already completed. Skipping.")
        return

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

    # 3. Download the playlist (always required)
    episode_dir = get_episode_dir(anime_name, ep_num, download_dir)
    playlist_path = downloader.fetch_playlist(playlist_url, episode_dir)
    if not playlist_path:
        return  # Error message is logged in the downloader

    if getattr(args, "m3u8_only", False):
        logger.success(
            f"Saved playlist only for Episode {ep_num} at {playlist_path} (m3u8-only mode)."
        )
        return

    # 4. Download segments from the playlist
    download_success = downloader.download_from_playlist_cli(playlist_path, args.threads)
    if download_success:
        # 5. Compile the downloaded segments into a single video file
        output_path = get_video_path(anime_name, ep_num, download_dir)
        # For CLI, we can create a simple tqdm progress bar for compilation
        with tqdm(
            total=100, desc=f"Compiling Ep. {ep_num}", unit="%", leave=False
        ) as pbar:

            def update_pbar(percent):
                pbar.n = int(percent)
                pbar.refresh()

            compilation_success = downloader.compile_video(
                episode_dir, output_path, progress_callback=update_pbar
            )
            
            if not compilation_success:
                logger.error(f"Failed to compile Episode {ep_num}")
                raise Exception(f"Video compilation failed for Episode {ep_num}")
    else:
        logger.error(f"Failed to download all segments for Episode {ep_num}")
        raise Exception(f"Segment download failed for Episode {ep_num}")

        # 6. Send a desktop notification upon completion
        try:
            notification.notify(
                title="Animepahe-dl",
                message=f"Finished downloading Ep {ep_num} of {anime_name}",
                app_name="Animepahe Downloader",
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")


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
        with open(constants.MY_ANIME_LIST_FILE, "r", encoding="utf-8") as f:
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
    
    # Send notification about new episodes found
    try:
        notification.notify(
            title="Animepahe-dl - New Episodes",
            message=f"Found {len(download_queue)} new episodes to download",
            app_name="Animepahe Downloader",
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")
    
    for item in download_queue:
        download_single_episode(api, downloader, item, args, app_config)

    logger.success("Update check finished!")
    
    # Send completion notification
    try:
        notification.notify(
            title="Animepahe-dl - Update Complete",
            message=f"Downloaded {len(download_queue)} new episodes",
            app_name="Animepahe Downloader",
            timeout=10
        )
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def manage_my_list():
    """
    Allows the user to add or remove anime from their personal list using fzf.
    """
    try:
        with open(constants.MY_ANIME_LIST_FILE, "r+", encoding="utf-8") as f:
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
    # Setup signal handling for graceful shutdown
    signal_handler = setup_signal_handling()
    
    # Ensure all external dependencies are met before starting
    check_dependencies()
    # Load user configuration from file and apply base_url override early
    app_config = config_manager.load_config()
    if "base_url" in app_config and app_config["base_url"] != constants.get_base_url():
        constants.set_base_url(app_config["base_url"])

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
    # Determine SSL verification preference
    # (Argument parsed below; temporarily store to apply after parse.)
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run update check once and exit (for cron jobs).",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (background service for continuous updates).",
    )
    parser.add_argument(
        "--daemon-action",
        type=str,
        choices=["start", "stop", "restart", "status"],
        help="Daemon management actions (start, stop, restart, status).",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable SSL certificate verification (INSECURE: use only if certificates are broken).",
    )
    parser.add_argument(
        "--m3u8-only",
        action="store_true",
        help="Fetch and save the episode m3u8 playlist only; skip segment download and compilation.",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Disable multi-selection mode (select only one anime at a time).",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Use traditional CLI mode instead of interactive mode.",
    )
    parser.add_argument(
        "--install-completions",
        action="store_true",
        help="Install shell completions for bash/zsh.",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration.",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show download history.",
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help="Search for anime without downloading.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging.",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play the episode(s) directly using m3u8 stream (requires media player).",
    )
    parser.add_argument(
        "--player",
        type=str,
        default="",
        help="Specify media player to use (mpv, vlc, ffplay). Auto-detects if not specified.",
    )

    args = parser.parse_args()
    
    # Set verbose logging if requested
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger.info("Verbose logging enabled")
    
    # Handle special commands first
    if args.install_completions:
        from .completions import install_completions
        install_completions()
        return
    
    if args.config:
        from ..utils.console import print_config_info
        print_config_info(app_config)
        return
    
    if args.history:
        from ..utils.console import console
        console.print("[dim]Download history feature coming soon![/dim]")
        return

    # Force insecure SSL always
    api = AnimePaheAPI(verify_ssl=False)
    downloader = Downloader(api)

    # --- Auto-update Cache ---
    cache_count = api.download_anime_list_cache()

    if cache_count == -1:
        logger.warning("Cache update failed; proceeding with existing cache (if any).")
    else:
        logger.info(f"Cache update complete. Entries: {cache_count}")
        if cache_count == 0:
            logger.error(
                "Cache file written but contains zero entries. Base URL may be wrong or site layout changed."
            )

    # --- Mode Selection ---
    if args.updates:
        # Run in a loop to periodically check for updates
        while True:
            run_update_check(api, downloader, args, app_config)
            if args.run_once:
                break
            logger.info(
                f"Waiting for {constants.UPDATE_CHECK_INTERVAL_MINUTES} minutes before next check..."
            )
            time.sleep(constants.UPDATE_CHECK_INTERVAL_MINUTES * 60)
    elif args.manage:
        manage_my_list()
    elif args.daemon:
        # Daemon mode - run as background service
        from ..services.daemon_service import run_daemon_command
        run_daemon_command("start")
    elif args.daemon_action:
        # Daemon management commands
        from ..services.daemon_service import run_daemon_command
        run_daemon_command(args.daemon_action)
    elif args.search_only:
        # Search-only mode
        selected_anime_list = choose_anime(api, args.name, cache_count, multi=not args.single)
        if selected_anime_list:
            from ..utils.console import print_anime_table
            print_anime_table(selected_anime_list)
        return
    elif args.play:
        # Play mode - stream episodes directly
        media_player = detect_media_player(args.player)
        if not media_player:
            logger.error("No compatible media player found. Please install mpv, vlc, ffplay, or mplayer.")
            logger.info("Installation suggestions:")
            logger.info("  Ubuntu/Debian: sudo apt install mpv")
            logger.info("  macOS: brew install mpv")
            logger.info("  Windows: Download from https://mpv.io/")
            return
        
        # Search for anime
        selected_anime_list = choose_anime(api, args.name, cache_count, multi=not args.single)
        if not selected_anime_list:
            return
        
        # Process each selected anime for playing
        for selected_anime in selected_anime_list:
            anime_name = selected_anime["title"]
            anime_slug = selected_anime["session"]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {anime_name}")
            logger.info(f"{'='*60}")
            
            # Fetch episode data
            episode_data = api.fetch_episode_data(anime_name, anime_slug)
            if not episode_data:
                logger.error(f"Could not fetch episodes for {anime_name}. Skipping.")
                continue
            
            # Create Anime object and populate episodes
            anime = Anime(name=anime_name, slug=anime_slug)
            max_ep = 0
            for ep_data in episode_data:
                ep_num = int(ep_data["episode"])
                if ep_num > max_ep:
                    max_ep = ep_num
                episode = Episode(
                    number=ep_num,
                    session=ep_data["session"]
                )
                anime.episodes.append(episode)
            
            # Select episodes to play
            if not args.episodes:
                episodes_to_play = select_episodes(anime)
            else:
                episodes_to_play = parse_episode_selection(args.episodes, max_ep)
            
            if not episodes_to_play:
                logger.info(f"No episodes selected for {anime_name}.")
                continue
            
            logger.info(f"Selected Episodes to play: {', '.join(map(str, episodes_to_play))}")
            
            # Play each episode
            for ep_num in episodes_to_play:
                episode = anime.get_episode(ep_num)
                if not episode:
                    logger.warning(f"Episode {ep_num} not found for {anime_name}.")
                    continue
                
                success = play_episode_stream(
                    api, anime_name, anime_slug, ep_num, 
                    episode.session, args.quality, args.audio, media_player
                )
                
                if not success:
                    logger.error(f"Failed to play {anime_name} Episode {ep_num}")
                    continue
                
                # For sequential playback, ask user if they want to continue
                if len(episodes_to_play) > 1 and ep_num != episodes_to_play[-1]:
                    try:
                        next_ep = episodes_to_play[episodes_to_play.index(ep_num) + 1] if ep_num in episodes_to_play else ep_num + 1
                        response = input(f"\nPress Enter to play next episode ({next_ep}), or 'q' to quit: ").strip().lower()
                        if response == 'q':
                            logger.info("Playback stopped by user.")
                            break
                    except KeyboardInterrupt:
                        logger.info("\nPlayback interrupted by user.")
                        break
        
        logger.success("Playback session finished!")
        return
    elif any([args.name, args.episodes, args.updates, args.single, args.cli]) and not args.play:
        # Traditional CLI mode - when specific flags are used or --cli is specified
        # --- Default Mode: Search and Download ---
        # 1. Search for one or more anime (multi-selection is default)
        selected_anime_list = choose_anime(api, args.name, cache_count, multi=not args.single)
        if not selected_anime_list:
            return

        # 2. Process each selected anime
        all_download_tasks = []
        download_dir = app_config["download_directory"]
        
        for selected_anime in selected_anime_list:
            anime_name = selected_anime["title"]
            anime_slug = selected_anime["session"]

            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {anime_name}")
            logger.info(f"{'='*60}")

            # Add the selected anime to the user's personal list
            try:
                with open(constants.MY_ANIME_LIST_FILE, "a+", encoding="utf-8") as f:
                    f.seek(0)
                    existing_list = f.read()
                    if anime_name not in existing_list:
                        f.write(f"{anime_name}\n")
            except IOError as e:
                logger.warning(f"Could not write to anime list file: {e}")

            # 3. Fetch all episode data for the selected anime
            episode_data = api.fetch_episode_data(anime_name, anime_slug)
            if not episode_data:
                logger.error(f"Could not fetch any episodes for {anime_name}. Skipping.")
                continue

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
                episode = Episode(
                    number=ep_num,
                    session=ep_data["session"]
                )
                # Set download status based on file existence
                if os.path.exists(video_path):
                    episode.mark_as_downloaded(video_path)
                anime.episodes.append(episode)

            # 5. Select which episodes to download
            if not args.episodes:
                # If no specific episodes are provided via flags, prompt the user
                episodes_to_download = select_episodes(anime)
            else:
                # Otherwise, use the episodes from the command line
                episodes_to_download = parse_episode_selection(args.episodes, max_ep)

            if not episodes_to_download:
                logger.info(f"No episodes selected for {anime_name}.")
                continue

            logger.info(f"Selected Episodes for {anime_name}: {', '.join(map(str, episodes_to_download))}")

            # 6. Queue episodes for download
            for ep_num in episodes_to_download:
                episode = anime.get_episode(ep_num)
                if not episode:
                    logger.warning(f"Episode {ep_num} not found for {anime_name}.")
                    continue
                if episode.is_downloaded:
                    logger.success(f"✓ Resuming: {anime_name} Episode {ep_num} already downloaded. Skipping.")
                    continue

                all_download_tasks.append({
                    "name": anime.name,
                    "slug": anime.slug,
                    "episode_num": episode.number,
                    "episode_session": episode.session,
                })

        # 7. Download all queued episodes concurrently
        if not all_download_tasks:
            logger.info("No episodes to download.")
            return

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting download of {len(all_download_tasks)} episode(s) across {len(selected_anime_list)} anime")
        logger.info(f"{'='*60}\n")

        # Register shutdown callback to cancel downloads
        executor_ref = None
        
        def shutdown_callback():
            if executor_ref:
                logger.info("Cancelling active downloads...")
                executor_ref.shutdown(wait=False)
        
        register_shutdown_callback(shutdown_callback)
        
        try:
            with ThreadPoolExecutor(max_workers=args.concurrent_downloads) as executor:
                executor_ref = executor
                futures = []
                for task in all_download_tasks:
                    if is_shutdown_requested():
                        logger.info("Shutdown requested, stopping new downloads")
                        break
                    
                    future = executor.submit(
                        download_single_episode,
                        api,
                        downloader,
                        task,
                        args,
                        app_config,
                    )
                    futures.append(future)

                # Create a mapping of futures to tasks for better error reporting
                future_to_task = {}
                for i, future in enumerate(futures):
                    if i < len(all_download_tasks):
                        future_to_task[future] = all_download_tasks[i]

                with tqdm(total=len(futures), desc="Overall Progress") as pbar:
                    failed_downloads = []
                    for future in as_completed(futures):
                        if is_shutdown_requested():
                            logger.info("Shutdown requested, stopping download processing")
                            break
                        
                        task = future_to_task.get(future, {"name": "Unknown", "episode_num": "Unknown"})
                        anime_name = task.get("name", "Unknown")
                        episode_num = task.get("episode_num", "Unknown")
                        
                        try:
                            future.result()  # Wait for the download to complete
                            logger.success(f"✓ Completed: {anime_name} Episode {episode_num}")
                        except Exception as e:
                            error_msg = str(e)
                            if "Segment download failed" in error_msg:
                                logger.error(f"An episode download failed: {anime_name} Episode {episode_num} - Some segments could not be downloaded")
                            elif "Video compilation failed" in error_msg:
                                logger.error(f"An episode download failed: {anime_name} Episode {episode_num} - Video compilation failed")
                            else:
                                logger.error(f"An episode download failed: {anime_name} Episode {episode_num}")
                                logger.error(f"Error details: {error_msg}")
                            
                            if args.verbose:
                                import traceback
                                logger.error(f"Full traceback: {traceback.format_exc()}")
                            failed_downloads.append(f"{anime_name} Episode {episode_num}")
                        pbar.update(1)
                    
                    if failed_downloads:
                        logger.warning(f"Failed downloads: {', '.join(failed_downloads)}")
                        logger.info("You can retry these episodes later - they will resume from where they left off.")
        
        except KeyboardInterrupt:
            logger.info("Download interrupted by user")
            return
        finally:
            executor_ref = None

        logger.success("All selected downloads are finished!")
    else:
        # Default: Launch interactive mode
        from .interactive import run_interactive_mode
        run_interactive_mode()
