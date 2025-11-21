# API Documentation

This document provides detailed information about the AnimePahe Downloader API and its components.

## Table of Contents

- [Core Classes](#core-classes)
- [API Client](#api-client)
- [Downloader](#downloader)
- [Models](#models)
- [Configuration](#configuration)
- [Utilities](#utilities)
- [Examples](#examples)

## Core Classes

### AnimePaheAPI

The main API client for interacting with AnimePahe.

```python
from anime_downloader.api import AnimePaheAPI

api = AnimePaheAPI(verify_ssl=False)
```

#### Methods

##### `search(query: str) -> List[Dict[str, str]]`

Search for anime by name.

**Parameters:**
- `query` (str): Search query string

**Returns:**
- List of dictionaries containing anime information:
  - `title` (str): Anime title
  - `session` (str): Anime session ID/slug

**Example:**
```python
results = api.search("Naruto")
for anime in results:
    print(f"{anime['title']} - {anime['session']}")
```

##### `fetch_episode_data(anime_name: str, anime_slug: str) -> List[Dict[str, Any]]`

Fetch all episodes for a given anime.

**Parameters:**
- `anime_name` (str): Name of the anime
- `anime_slug` (str): Anime session ID

**Returns:**
- List of episode dictionaries containing:
  - `episode` (str): Episode number
  - `session` (str): Episode session ID

**Example:**
```python
episodes = api.fetch_episode_data("Naruto", "naruto-slug")
print(f"Found {len(episodes)} episodes")
```

##### `get_stream_url(anime_slug: str, episode_session: str, quality: str, audio: str) -> Optional[str]`

Get the stream URL for a specific episode.

**Parameters:**
- `anime_slug` (str): Anime session ID
- `episode_session` (str): Episode session ID
- `quality` (str): Desired quality ("best", "1080", "720", etc.)
- `audio` (str): Audio language ("jpn" or "eng")

**Returns:**
- Stream URL string or None if not found

**Example:**
```python
stream_url = api.get_stream_url(
    "naruto-slug",
    "episode-1-session",
    quality="1080",
    audio="jpn"
)
```

##### `get_playlist_url(stream_url: str) -> Optional[str]`

Extract the m3u8 playlist URL from a stream page.

**Parameters:**
- `stream_url` (str): Stream page URL

**Returns:**
- M3U8 playlist URL or None

##### `download_anime_list_cache() -> int`

Download and cache the full anime list.

**Returns:**
- Number of entries cached, -1 on failure, 0 if empty

### Downloader

Handles downloading and processing of video segments.

```python
from anime_downloader.downloader import Downloader

downloader = Downloader(api)
```

#### Methods

##### `fetch_playlist(playlist_url: str, output_dir: str) -> Optional[str]`

Download the m3u8 playlist file.

**Parameters:**
- `playlist_url` (str): URL of the playlist
- `output_dir` (str): Directory to save the playlist

**Returns:**
- Path to downloaded playlist or None

##### `download_from_playlist_cli(playlist_path: str, num_threads: int) -> bool`

Download all segments from a playlist (CLI version with progress bar).

**Parameters:**
- `playlist_path` (str): Path to the playlist file
- `num_threads` (int): Number of concurrent download threads

**Returns:**
- True if successful, False otherwise

##### `compile_video(segment_dir: str, output_path: str, progress_callback: Optional[Callable]) -> bool`

Compile downloaded segments into a single video file.

**Parameters:**
- `segment_dir` (str): Directory containing segments
- `output_path` (str): Output video file path
- `progress_callback` (Optional[Callable]): Progress callback function

**Returns:**
- True if successful, False otherwise

## Models

### Anime

Represents an anime series.

```python
from anime_downloader.models import Anime, Episode

anime = Anime(name="Naruto", slug="naruto-slug")
```

**Attributes:**
- `name` (str): Anime title
- `slug` (str): Anime session ID
- `episodes` (List[Episode]): List of episodes
- `source_file_path` (Optional[str]): Source file path

**Methods:**
- `get_episode(episode_number: int) -> Optional[Episode]`: Get episode by number

### Episode

Represents a single episode.

```python
episode = Episode(number=1, session="ep1-session", is_downloaded=False)
```

**Attributes:**
- `number` (int): Episode number
- `session` (str): Episode session ID
- `is_downloaded` (bool): Download status

## Configuration

### Config Manager

Manages application configuration.

```python
from anime_downloader import config_manager

# Load configuration
config = config_manager.load_config()

# Save configuration
config_manager.save_config(config)
```

**Default Configuration:**
```python
{
    "base_url": "https://animepahe.com",
    "quality": "best",
    "audio": "jpn",
    "threads": 100,
    "download_directory": "~/Videos/Anime",
    "update_interval_hours": 5,
    "allow_insecure_ssl": True
}
```

## Utilities

### Cache

Simple file-based caching system.

```python
from anime_downloader.cache import get_cache

cache = get_cache()

# Store value
cache.set("key", {"data": "value"}, ttl=3600)

# Retrieve value
data = cache.get("key", default=None)

# Delete value
cache.delete("key")

# Clear all cache
cache.clear()
```

### Retry Decorator

Retry failed operations with exponential backoff.

```python
from anime_downloader.utils import retry

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def unstable_function():
    # May fail occasionally
    pass
```

### Rate Limiter

Limit API call frequency.

```python
from anime_downloader.utils import RateLimiter

limiter = RateLimiter(calls_per_second=5.0)

@limiter
def api_call():
    # Will be rate limited
    pass
```

## Examples

### Basic Download

```python
from anime_downloader.api import AnimePaheAPI
from anime_downloader.downloader import Downloader
from anime_downloader.models import Anime, Episode

# Initialize
api = AnimePaheAPI(verify_ssl=False)
downloader = Downloader(api)

# Search for anime
results = api.search("Naruto")
anime_data = results[0]

# Fetch episodes
episodes = api.fetch_episode_data(
    anime_data['title'],
    anime_data['session']
)

# Download first episode
episode = episodes[0]
stream_url = api.get_stream_url(
    anime_data['session'],
    episode['session'],
    quality="1080",
    audio="jpn"
)

playlist_url = api.get_playlist_url(stream_url)
playlist_path = downloader.fetch_playlist(playlist_url, "/tmp/episode1")
downloader.download_from_playlist_cli(playlist_path, num_threads=50)
downloader.compile_video("/tmp/episode1", "/tmp/episode1.mp4")
```

### Async Download

```python
import asyncio
from anime_downloader.async_downloader import download_episode_async

async def download():
    success = await download_episode_async(
        segments=segment_urls,
        key=decryption_key,
        media_sequence=0,
        output_dir="/tmp/episode",
        max_concurrent=50
    )
    return success

asyncio.run(download())
```

### Custom Progress Callback

```python
def progress_callback(current, total, speed_mbps):
    percent = (current / total) * 100
    print(f"Progress: {percent:.1f}% - {speed_mbps:.2f} MB/s")

downloader.download_from_playlist_cli(
    playlist_path,
    num_threads=50,
    progress_callback=progress_callback
)
```

### Using Cache

```python
from anime_downloader.cache import get_cache

cache = get_cache()

# Cache search results
def search_with_cache(query):
    cache_key = f"search_{query}"
    results = cache.get(cache_key)
    
    if results is None:
        results = api.search(query)
        cache.set(cache_key, results, ttl=3600)  # Cache for 1 hour
    
    return results
```

### Error Handling

```python
from anime_downloader.utils import retry
from anime_downloader.logger import logger

@retry(max_attempts=3, delay=1.0, backoff=2.0)
def download_with_retry():
    try:
        # Download logic
        pass
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise

try:
    download_with_retry()
except Exception as e:
    logger.critical(f"All retry attempts failed: {e}")
```

## Type Hints

The codebase uses type hints for better IDE support and type checking:

```python
from typing import List, Dict, Optional, Callable

def fetch_episodes(
    anime_slug: str,
    quality: str = "1080"
) -> List[Dict[str, str]]:
    """Fetch episodes with type hints."""
    pass
```

## Testing

Example test case:

```python
import pytest
from anime_downloader.models import Anime, Episode

def test_anime_creation():
    anime = Anime(name="Test", slug="test-slug")
    assert anime.name == "Test"
    assert anime.slug == "test-slug"
    assert len(anime.episodes) == 0

def test_get_episode():
    anime = Anime(name="Test", slug="test-slug")
    anime.episodes = [
        Episode(number=1, session="ep1"),
        Episode(number=2, session="ep2"),
    ]
    
    ep = anime.get_episode(1)
    assert ep is not None
    assert ep.number == 1
```

## Best Practices

1. **Always use context managers** for file operations
2. **Handle exceptions gracefully** with try-except blocks
3. **Use type hints** for better code documentation
4. **Implement retry logic** for network operations
5. **Cache frequently accessed data** to reduce API calls
6. **Use async operations** for I/O-bound tasks
7. **Validate user input** before processing
8. **Log important events** for debugging

## Performance Tips

1. **Increase thread count** for faster downloads (up to 100)
2. **Use async downloader** for better concurrency
3. **Enable caching** to reduce redundant API calls
4. **Download lower quality** for faster speeds
5. **Use SSD storage** for better I/O performance
6. **Close unused connections** to free resources

## Troubleshooting

### Common Issues

**Import Errors:**
```python
# Ensure package is installed
pip install -e .
```

**SSL Errors:**
```python
# Use insecure mode (not recommended for production)
api = AnimePaheAPI(verify_ssl=False)
```

**Rate Limiting:**
```python
# Use rate limiter
from anime_downloader.utils import RateLimiter
limiter = RateLimiter(calls_per_second=2.0)
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to the API.

## License

MIT License - see [LICENSE](../LICENSE) for details.
