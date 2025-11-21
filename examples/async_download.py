#!/usr/bin/env python3
"""
Async download example.

This script demonstrates how to use the async downloader
for improved performance.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anime_downloader.api import AnimePaheAPI
from anime_downloader.async_downloader import download_episode_async
from anime_downloader.downloader import Downloader
from anime_downloader.logger import logger


async def download_episode(api, downloader, anime_data, episode_data, output_dir):
    """Download a single episode asynchronously."""
    logger.info(f"Downloading Episode {episode_data['episode']}...")

    # Get stream and playlist URLs
    stream_url = api.get_stream_url(
        anime_data["session"], episode_data["session"], quality="720", audio="jpn"
    )

    if not stream_url:
        logger.error(f"Could not get stream URL for episode {episode_data['episode']}")
        return False

    playlist_url = api.get_playlist_url(stream_url)
    if not playlist_url:
        logger.error(f"Could not get playlist URL for episode {episode_data['episode']}")
        return False

    # Download playlist
    episode_dir = output_dir / episode_data["episode"]
    playlist_path = downloader.fetch_playlist(playlist_url, str(episode_dir))

    if not playlist_path:
        logger.error(f"Could not download playlist for episode {episode_data['episode']}")
        return False

    # Get playlist details
    details = downloader.get_playlist_details(playlist_path)
    if not details:
        logger.error(f"Could not parse playlist for episode {episode_data['episode']}")
        return False

    # Download key
    key_response = api._request(details["key_url"])
    if not key_response:
        logger.error(f"Could not download key for episode {episode_data['episode']}")
        return False

    # Download segments asynchronously
    def progress_callback(completed, total, speed):
        logger.info(
            f"Episode {episode_data['episode']}: {completed}/{total} segments "
            f"({speed:.2f} MB/s)"
        )

    success = await download_episode_async(
        segments=details["segments"],
        key=key_response.data,
        media_sequence=details["media_sequence"],
        output_dir=str(episode_dir),
        max_concurrent=50,
        progress_callback=progress_callback,
    )

    if not success:
        logger.error(f"Failed to download segments for episode {episode_data['episode']}")
        return False

    # Compile video
    output_file = output_dir / f"Episode_{episode_data['episode']}.mp4"
    logger.info(f"Compiling Episode {episode_data['episode']}...")

    success = downloader.compile_video(str(episode_dir), str(output_file))

    if success:
        logger.success(f"Episode {episode_data['episode']} complete: {output_file}")
    else:
        logger.error(f"Failed to compile episode {episode_data['episode']}")

    return success


async def main():
    """Main async function."""
    # Initialize
    api = AnimePaheAPI(verify_ssl=False)
    downloader = Downloader(api)

    # Search
    query = "Naruto"
    logger.info(f"Searching for: {query}")
    results = api.search(query)

    if not results:
        logger.error("No results found")
        return

    selected = results[0]
    logger.info(f"Selected: {selected['title']}")

    # Fetch episodes
    episodes = api.fetch_episode_data(selected["title"], selected["session"])
    if not episodes:
        logger.error("No episodes found")
        return

    logger.info(f"Found {len(episodes)} episodes")

    # Download first 3 episodes concurrently
    output_dir = Path("./downloads") / selected["title"]
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        download_episode(api, downloader, selected, episode, output_dir)
        for episode in episodes[:3]
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = sum(1 for r in results if r is True)
    logger.info(f"\nCompleted: {successful}/{len(tasks)} episodes downloaded successfully")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nDownload cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
        sys.exit(1)
