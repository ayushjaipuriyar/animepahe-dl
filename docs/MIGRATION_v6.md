# Migration Guide: v5.4.0 → v6.0.0

This guide helps you migrate from animepahe-dl v5.4.0 to v6.0.0, which includes several breaking changes and new features.

## 🚨 Breaking Changes

### 1. Episode Model API Changes

**Before (v5.4.0):**
```python
# This will now raise TypeError
episode = Episode(
    number=1,
    session="abc123",
    is_downloaded=True  # ❌ No longer supported
)
```

**After (v6.0.0):**
```python
# Correct way to create episodes
episode = Episode(
    number=1,
    session="abc123"
)

# Set download status properly
if os.path.exists(video_path):
    episode.mark_as_downloaded(video_path)

# Check download status
if episode.is_downloaded:  # This is now a property
    print("Episode is downloaded")
```

### 2. Import Structure Changes

**Before (v5.4.0):**
```python
# This will now raise AttributeError
from anime_downloader import cli
video_path = cli.get_video_path(anime_name, ep_num, download_dir)
```

**After (v6.0.0):**
```python
# Correct import
from anime_downloader.cli.commands import get_video_path
video_path = get_video_path(anime_name, ep_num, download_dir)
```

### 3. Removed Modules

The following modules have been removed as they were duplicates or unused:

- `anime_downloader.services.api_service` → Use `anime_downloader.api.client`
- `anime_downloader.services.download_service` → Use `anime_downloader.api.downloader`
- `anime_downloader.core.base` → Removed (unused OOP base classes)
- `anime_downloader.core.interfaces` → Removed (unused interfaces)
- `anime_downloader.core.config` → Use `anime_downloader.utils.config_manager`
- `anime_downloader.controllers.*` → Removed (unused controller pattern)
- `anime_downloader.gui.widgets.*` → Removed (unused custom widgets)

**Migration:**
```python
# Before (v5.4.0)
from anime_downloader.services.api_service import AnimePaheAPIService
from anime_downloader.services.download_service import DownloadService

# After (v6.0.0)
from anime_downloader.api import AnimePaheAPI, Downloader
```

## ✨ New Features

### 1. Direct Streaming

Stream episodes without downloading:

```bash
# Stream single episode
animepahe-dl -n "Naruto" -e 1 --play

# Stream multiple episodes
animepahe-dl -n "Naruto" -e 1-5 --play

# Use specific media player
animepahe-dl -n "Naruto" -e 1 --play --player mpv
```

### 2. Desktop Notifications

Notifications are now enabled by default. Configure in `config.json`:

```json
{
  "notifications_enabled": true,
  "notification_sound": true
}
```

### 3. System Tray Support

The GUI now supports system tray:
- Close button minimizes to tray
- Right-click tray icon for context menu
- Toggle background monitoring
- Quick access to common actions

### 4. Daemon Mode

Run as background service:

```bash
# Start daemon
animepahe-dl --daemon

# Manage daemon
animepahe-dl --daemon-action start
animepahe-dl --daemon-action stop
animepahe-dl --daemon-action status
```

### 5. Linux Service Integration

Install as systemd service:

```bash
# Install service
./scripts/install-service.sh

# Manage service
sudo systemctl start animepahe-dl
sudo systemctl enable animepahe-dl
```

## 🔧 Configuration Changes

### New Configuration Options

Add these to your `config.json`:

```json
{
  "notifications_enabled": true,
  "update_interval_hours": 1,
  "media_player": "mpv",
  "streaming_quality": "best",
  "system_tray_enabled": true,
  "daemon_mode": false
}
```

## 🐛 Bug Fixes

### Episode Selection Fixed

The interactive mode now properly filters episodes:

```bash
# This now works correctly - only downloads episode 1
animepahe-dl -n "Naruto" -e 1

# Range selection also works properly
animepahe-dl -n "Naruto" -e 1-5
```

### GUI Improvements

- Fixed import errors in GUI workers
- Improved episode status tracking
- Better error handling and user feedback

## 📦 Dependencies

### New Dependencies

- `plyer` - For desktop notifications
- Enhanced PyQt6 integration for system tray

### Media Player Requirements

For streaming functionality, install one of:
- **mpv** (recommended): `sudo apt install mpv`
- **VLC**: Download from videolan.org
- **ffplay**: Usually included with ffmpeg
- **mplayer**: `sudo apt install mplayer`

## 🚀 Upgrade Steps

1. **Backup your configuration:**
   ```bash
   cp ~/.config/anime_downloader/config.json ~/.config/anime_downloader/config.json.backup
   ```

2. **Update the package:**
   ```bash
   uv tool upgrade animepahe-dl
   # or
   pip install --upgrade animepahe-dl
   ```

3. **Update your code** (if using as library):
   - Fix Episode constructor calls
   - Update import statements
   - Remove references to deleted modules

4. **Test the installation:**
   ```bash
   animepahe-dl --help
   animepahe-dl --gui  # Test GUI
   ```

5. **Configure new features:**
   - Enable notifications in config
   - Set up daemon mode if desired
   - Install systemd service if on Linux

## 🆘 Troubleshooting

### Common Issues

**Import Errors:**
```python
# If you see: AttributeError: module 'anime_downloader.cli' has no attribute 'get_video_path'
# Fix: Update import statement
from anime_downloader.cli.commands import get_video_path
```

**Episode Constructor Errors:**
```python
# If you see: TypeError: Episode.__init__() got an unexpected keyword argument 'is_downloaded'
# Fix: Remove is_downloaded parameter and use mark_as_downloaded() method
episode = Episode(number=1, session="abc123")
if downloaded:
    episode.mark_as_downloaded(file_path)
```

**Missing Modules:**
```python
# If you see: ModuleNotFoundError: No module named 'anime_downloader.services.api_service'
# Fix: Use the main API module
from anime_downloader.api import AnimePaheAPI
```

### Getting Help

If you encounter issues:

1. Check this migration guide
2. Review the [troubleshooting section](../README.md#-troubleshooting) in README
3. Open an issue on GitHub with:
   - Your operating system
   - Python version
   - Full error message
   - Steps to reproduce

## 📝 Summary

v6.0.0 brings significant improvements:
- ✅ Direct streaming capabilities
- ✅ Better desktop integration
- ✅ Background monitoring
- ✅ Cleaner codebase
- ✅ Fixed episode selection bugs

The breaking changes primarily affect library usage rather than CLI/GUI usage, making the upgrade smooth for most users.