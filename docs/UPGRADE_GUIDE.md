# Upgrade Guide

This guide helps you upgrade from older versions of animepahe-dl to the latest version.

## Table of Contents

- [Upgrading from 5.1.x to 5.2.x](#upgrading-from-51x-to-52x)
- [Upgrading from 5.0.x to 5.1.x](#upgrading-from-50x-to-51x)
- [Breaking Changes](#breaking-changes)
- [New Features](#new-features)
- [Migration Steps](#migration-steps)

## Upgrading from 5.1.x to 5.2.x

### What's New

- **Performance Improvements**: New async downloader for better concurrency
- **Caching System**: Reduces redundant API calls
- **Better Error Handling**: Improved retry logic and error messages
- **Type Hints**: Full type hint coverage for better IDE support
- **Testing**: Comprehensive test suite added
- **Documentation**: Enhanced documentation and examples

### Installation

```bash
pip install --upgrade animepahe-dl
```

### Configuration Changes

The configuration file format remains compatible, but new options are available:

```json
{
  "base_url": "https://animepahe.com",
  "quality": "best",
  "audio": "jpn",
  "threads": 100,
  "concurrent_downloads": 2,
  "download_directory": "~/Videos/Anime",
  "update_interval_hours": 5,
  "allow_insecure_ssl": true
}
```

**New Options:**
- `concurrent_downloads`: Number of episodes to download simultaneously (default: 2)

### API Changes

#### Async Downloader

New async download functionality:

```python
# Old way (still works)
downloader.download_from_playlist_cli(playlist_path, num_threads=50)

# New way (faster)
import asyncio
from anime_downloader.async_downloader import download_episode_async

await download_episode_async(
    segments=segments,
    key=key,
    media_sequence=0,
    output_dir="/path/to/output",
    max_concurrent=50
)
```

#### Caching

New caching system:

```python
from anime_downloader.cache import get_cache

cache = get_cache()
cache.set("key", value, ttl=3600)
value = cache.get("key")
```

#### Performance Monitoring

New performance tracking:

```python
from anime_downloader.performance import track_performance, Timer

@track_performance()
def my_function():
    pass

with Timer("operation") as timer:
    # code here
    pass
```

### CLI Changes

#### New Flags

- `--concurrent-downloads` or `-c`: Set concurrent episode downloads
- `--m3u8-only`: Fetch playlist only without downloading

**Example:**
```bash
# Download 3 episodes concurrently
animepahe-dl -n "Anime Name" -e 1-10 -c 3

# Fetch playlist only
animepahe-dl -n "Anime Name" -e 1 --m3u8-only
```

### Migration Steps

1. **Backup your configuration:**
   ```bash
   cp ~/.config/anime_downloader/config.json ~/.config/anime_downloader/config.json.bak
   ```

2. **Upgrade the package:**
   ```bash
   pip install --upgrade animepahe-dl
   ```

3. **Clear old cache (optional):**
   ```bash
   rm -rf ~/.config/anime_downloader/cache/
   ```

4. **Test the upgrade:**
   ```bash
   animepahe-dl --version
   animepahe-dl -n "Test Anime"
   ```

## Upgrading from 5.0.x to 5.1.x

### What's New

- Improved GUI interface
- Better error handling
- Enhanced logging
- Bug fixes

### Installation

```bash
pip install --upgrade animepahe-dl
```

### Configuration Changes

No breaking changes. Configuration file format remains the same.

### Migration Steps

1. Upgrade the package:
   ```bash
   pip install --upgrade animepahe-dl
   ```

2. Update cache:
   ```bash
   animepahe-dl --updates --run-once
   ```

## Breaking Changes

### Version 5.2.x

**None** - Fully backward compatible with 5.1.x

### Version 5.1.x

**None** - Fully backward compatible with 5.0.x

### Version 5.0.x

- Minimum Python version increased to 3.8
- Configuration file location changed to follow XDG standards
- Some internal API methods renamed (if you're using the library)

## New Features by Version

### 5.2.x

- ✨ Async downloader for improved performance
- 💾 File-based caching system
- 📊 Performance monitoring and profiling
- 🧪 Comprehensive test suite
- 📚 Enhanced documentation
- 🐳 Docker support
- 🔧 Better error handling and retry logic
- 📝 Type hints throughout codebase
- ⚡ Concurrent episode downloads
- 🎯 Improved quality selection

### 5.1.x

- 🎨 Improved GUI interface
- 🔔 Desktop notifications
- 📋 Better episode selection
- 🐛 Bug fixes and stability improvements

### 5.0.x

- 🚀 Complete rewrite
- 🖥️ GUI interface added
- ⚙️ Configuration management
- 📦 Better packaging

## Common Issues

### Issue: Import Error After Upgrade

**Solution:**
```bash
pip uninstall animepahe-dl
pip install animepahe-dl
```

### Issue: Configuration Not Found

**Solution:**
```bash
# Check config location
python -c "from anime_downloader import config; print(config.BASE_DATA_DIR)"

# Recreate config
animepahe-dl --help  # This will create default config
```

### Issue: Cache Errors

**Solution:**
```bash
# Clear cache
rm -rf ~/.config/anime_downloader/cache/

# Update cache
animepahe-dl --updates --run-once
```

### Issue: SSL Certificate Errors

**Solution:**
```bash
# Use insecure mode (not recommended)
animepahe-dl --insecure -n "Anime Name"

# Or update config.json
{
  "allow_insecure_ssl": true
}
```

## Rollback Instructions

If you need to rollback to a previous version:

```bash
# Rollback to specific version
pip install animepahe-dl==5.1.0

# Restore configuration backup
cp ~/.config/anime_downloader/config.json.bak ~/.config/anime_downloader/config.json
```

## Getting Help

If you encounter issues during upgrade:

1. Check the [Troubleshooting Guide](../README.md#troubleshooting)
2. Search [existing issues](https://github.com/ayushjaipuriyar/animepahe-dl/issues)
3. Create a [new issue](https://github.com/ayushjaipuriyar/animepahe-dl/issues/new)

## Deprecation Notices

### Deprecated in 5.2.x

- None

### Deprecated in 5.1.x

- None

### Removed in 5.0.x

- Python 3.6 and 3.7 support
- Old configuration format

## Future Changes

### Planned for 6.0.x

- Plugin system
- Multiple source support
- Advanced filtering options
- Subtitle download support

Stay updated by watching the [repository](https://github.com/ayushjaipuriyar/animepahe-dl) and reading the [CHANGELOG](../CHANGELOG.md).
