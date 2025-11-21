#!/usr/bin/env python3
"""
Basic download example.

This script demonstrates how to use the anime_downloader API
to search for and download anime episodes.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anime_downloader.api import AnimePaheAPI
from anime_downloader.downloader import Downloader
from anime_downloader.logger import logger


def main():
    """Main function demonstrating basic download."""
    # Initialize API and downloader
    api = AnimePaheAPI(verify_ssl=False)
    downloader = Downloader(api)

    # Search for anime
    query = "Naruto"
    logger.info(f"Searching for: {query}")
    results = api.search(query)

    if not results:
        logger.error("No results found")
        return

    # Display results
    logger.info(f"Found {len(results)} results:")
    for i, anime in enumerate(results[:5], 1):
        logger.info(f"{i}. {anime['title']}")

    # Select first result
    selected = results[0]
    logger.info(f"\nSelected: {selected['title']}")

    # Fetch episodes
    logger.info("Fetching episodes...")
    episodes = api.fetch_episode_data(selected["title"], selected["session"])

    if not episodes:
        logger.error("No episodes found")
        return

    logger.info(f"Found {len(episodes)} episodes")

    # Download first episode
    episode = episodes[0]
    logger.info(f"\nDownloading Episode {episode['episode']}...")

    # Get stream URL
    stream_url = api.get_stream_url(
        selected["session"], episode["session"], quality="720", audio="jpn"
    )

    if not stream_url:
        logger.error("Could not get stream URL")
        return

    # Get playlist
    playlist_url = api.get_playlist_url(stream_url)
    if not playlist_url:
        logger.error("Could not get playlist URL")
        return

    # Download playlist and segments
    output_dir = Path("./downloads") / selected["title"] / episode["episode"]
    output_dir.mkdir(parents=True, exist_ok=True)

    playlist_path = downloader.fetch_playlist(playlist_url, str(output_dir))
    if not playlist_path:
        logger.error("Could not download playlist")
        return

    logger.info("Downloading segments...")
    success = downloader.download_from_playlist_cli(playlist_path, num_threads=50)

    if not success:
        logger.error("Failed to download segments")
        return

    # Compile video
    output_file = output_dir.parent / f"Episode_{episode['episode']}.mp4"
    logger.info(f"Compiling video to {output_file}...")

    success = downloader.compile_video(str(output_dir), str(output_file))

    if success:
        logger.success(f"Download complete: {output_file}")
    else:
        logger.error("Failed to compile video")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nDownload cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        sys.exit(1)
