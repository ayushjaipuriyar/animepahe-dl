# Examples

This directory contains example scripts demonstrating various features of the anime_downloader package.

## Available Examples

### basic_download.py

Demonstrates basic usage of the API:
- Searching for anime
- Fetching episode data
- Downloading a single episode
- Compiling the final video

**Usage:**
```bash
python examples/basic_download.py
```

### async_download.py

Shows how to use async downloads for better performance:
- Concurrent episode downloads
- Async segment downloading
- Progress tracking

**Usage:**
```bash
python examples/async_download.py
```

### custom_config.py

Demonstrates configuration management:
- Loading and saving config
- Customizing download settings
- Managing cache

**Usage:**
```bash
python examples/custom_config.py
```

### batch_download.py

Shows how to download multiple episodes:
- Episode range selection
- Batch processing
- Error handling

**Usage:**
```bash
python examples/batch_download.py
```

## Requirements

All examples require the package to be installed:

```bash
pip install -e .
```

Or with development dependencies:

```bash
pip install -e ".[dev]"
```

## Notes

- Examples create a `downloads/` directory in the current working directory
- Modify the anime name and episode numbers as needed
- Check the logs for detailed progress information
- Press Ctrl+C to cancel downloads gracefully

## Tips

1. **Adjust thread count** for your network speed:
   ```python
   downloader.download_from_playlist_cli(playlist_path, num_threads=100)
   ```

2. **Change quality** for faster downloads:
   ```python
   stream_url = api.get_stream_url(..., quality="720", ...)
   ```

3. **Use async downloads** for multiple episodes:
   ```python
   await download_episode_async(...)
   ```

4. **Enable debug logging** for troubleshooting:
   ```python
   from anime_downloader.logger import logger
   logger.level("DEBUG")
   ```
