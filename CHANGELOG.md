# CHANGELOG

<!-- version list -->

## v6.0.0 (2025-12-13)

### Features

- **Direct Streaming**: Added ability to play episodes directly using m3u8 streams without downloading
- **Media Player Integration**: Auto-detection and support for mpv, VLC, ffplay, and mplayer
- **GUI Streaming Support**: Added play button in GUI for direct episode streaming
- **Desktop Notifications**: Enabled desktop notifications using plyer library for download completion and new episodes
- **System Tray Support**: Added QSystemTrayIcon integration with context menu and background operation
- **Daemon Mode**: Implemented continuous background monitoring with `--daemon` and `--daemon-action` flags
- **Systemd Integration**: Added Linux service support with installation script for automatic startup
- **Enhanced Episode Selection**: Fixed episode range filtering in interactive mode (e.g., "1", "1-5", "1,3,5")
- **Improved CLI Arguments**: Enhanced mpv command line arguments with proper streaming headers and buffering
- **Code Architecture Cleanup**: Removed duplicate code and unused OOP refactoring components

### Bug Fixes

- **Episode Model Constructor**: Fixed `Episode.__init__()` to use proper status management instead of `is_downloaded` parameter
- **GUI Workers Import**: Fixed import errors for `get_video_path` function in GUI workers
- **CLI Scoping Issue**: Resolved `UnboundLocalError` for `Anime` class in CLI commands
- **Interactive Mode Filtering**: Fixed episode filtering logic to properly parse and apply user selections
- **Media Player Launch**: Fixed mpv command line argument format and added proper error handling

### Breaking Changes

- **Episode Model API**: The `Episode` constructor no longer accepts `is_downloaded` parameter. Use `mark_as_downloaded()` method instead
- **Import Structure**: Moved utility functions to proper modules. Import `get_video_path` from `anime_downloader.cli.commands` instead of `anime_downloader.cli`
- **Removed Modules**: Eliminated duplicate services and unused OOP components:
  - Removed `anime_downloader.services.api_service.py`
  - Removed `anime_downloader.services.download_service.py`
  - Removed `anime_downloader.core.base.py`, `anime_downloader.core.interfaces.py`, `anime_downloader.core.config.py`
  - Removed entire `anime_downloader.controllers/` directory
  - Removed unused GUI widgets: `anime_downloader.gui.widgets/`

### Performance Improvements

- **Reduced Code Duplication**: Eliminated redundant implementations improving maintainability
- **Optimized Imports**: Cleaned up import structure reducing startup time
- **Enhanced Streaming**: Added buffering and network timeout options for better streaming performance

## v5.4.0 (2025-11-21)

### Features

- Comprehensive project improvements with UV migration
  ([`e2aabf7`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/e2aabf76e8e65232e3463347963005bf04c71e2e))


## v5.3.0 (2025-10-04)


## v5.2.1 (2025-10-04)

### Bug Fixes

- Fix the aur package
  ([`cf46518`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/cf46518dc5aae3460cd9f388a689cbfa4b83c942))


## v5.2.0 (2025-10-04)

### Features

- M3u8 saving
  ([`04b572b`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/04b572b852a082823accb13f68d0428e291e5a6f))


## v5.1.5 (2025-07-29)

### Bug Fixes

- 🐛 small fix to the deploy
  ([`5cbadd6`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/5cbadd68b69c09b3bda586f704dec3a003b28b85))


## v5.1.4 (2025-07-29)

### Bug Fixes

- 🐛 fix the version logic
  ([`bfa2b20`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/bfa2b20471f76ec2c0fb802422b07c8ac1b270a7))


## v5.1.3 (2025-07-29)


## v5.1.2 (2025-07-29)


## v5.1.1 (2025-07-29)

### Bug Fixes

- 🐛 minro fix
  ([`75ecba4`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/75ecba47c99282d7cf83ee3027fea77c82ee0c75))


## v5.1.0 (2025-07-29)

### Bug Fixes

- 🐛 forgot @
  ([`abd64d6`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/abd64d6dbbe65a5934ae4c20383a0b2f361fe705))


## v5.0.0 (2025-07-29)


## v4.0.0 (2025-07-29)

### Bug Fixes

- 🐛 relase some issue with oidc
  ([`3491cf2`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/3491cf2a0f9dbe346faace3edb6eca3c8f27d3da))

### Breaking Changes

- 🧨 PYPI PUBLISH


## v3.0.0 (2025-07-29)


## v2.0.0 (2025-07-29)

### Bug Fixes

- 🐛 release
  ([`6e24644`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/6e24644139a940e61195db4fcff21a63b280d571))

- 🐛 release.yml Invalid workflow file: .github/workflows/rel
  ([`1483361`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/1483361933e06e447a1ff3af276f005c81e1a63c))

### Breaking Changes

- 🧨 PYPI RELEASE


## v1.0.0 (2025-07-29)

### Bug Fixes

- 🐛 release
  ([`aef36ad`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/aef36ad90ddf07362b6b213ab143707cc42b517a))

- 🐛 release fixing
  ([`c310c64`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/c310c64d6620dc3154fe94946dc58c2b3dc6eace))

- 🐛 semantic release issue
  ([`3d376de`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/3d376de14bf7bf629147595baa8221cf3daf4fb8))

### Features

- 🎸 Release
  ([`2efa8e9`](https://github.com/ayushjaipuriyar/animepahe-dl/commit/2efa8e9255ef077d276ef393c3d2405ae0dea6e4))

### Breaking Changes

- 🧨 First release to pypi

- 🧨 PYPI RELEASE


## v0.1.0 (2025-07-14)

- Initial Release
