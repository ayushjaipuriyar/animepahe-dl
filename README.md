# AnimePahe Downloader

[![PyPI version](https://badge.fury.io/py/animepahe-dl.svg)](https://badge.fury.io/py/animepahe-dl)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/ci.yml/badge.svg)](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/ci.yml)
[![Release](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/release.yml/badge.svg)](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/release.yml)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A feature-rich, high-performance anime downloader for AnimePahe with both CLI and GUI interfaces. Built with Python, featuring concurrent downloads, resume support, and cross-platform compatibility.

![Screenshot](ss1.png)

## 📋 Table of Contents

- [Highlights](#-highlights)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [For Developers](#️-for-developers)
- [Performance Tips](#-performance-tips)
- [Troubleshooting](#-troubleshooting)
- [Documentation](#-documentation)
- [Docker Support](#-docker-support)
- [Advanced Usage](#-advanced-usage)
- [New Features](#-new-features-in-v521)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

## ✨ Highlights

- 🚀 **High Performance**: Concurrent segment downloads with configurable thread pools
- 💾 **Smart Caching**: Reduces redundant API calls and improves response times
- 🔄 **Resume Support**: Continue interrupted downloads seamlessly
- 🎨 **Dual Interface**: Choose between CLI for automation or GUI for ease of use
- 🔔 **Desktop Notifications**: Get notified when downloads complete
- 🌐 **Cross-Platform**: Works on Windows, macOS, and Linux
- 📦 **Auto-Updates**: Automatic cache updates for the latest anime releases
- 🎯 **Flexible Selection**: Download single episodes, ranges, or entire series

## Features

*   **Search and Download**: Find any anime on AnimePahe and download it.
*   **Batch Downloads**: Download entire series or select specific episodes.
*   **Resume Support**: Resume interrupted downloads without starting over.
*   **Cross-Platform**: Works on Windows, macOS, and Linux.
*   **Desktop Notifications**: Get notified when your downloads are complete.
*   **Automatic Cache Updates**: Keep your local anime list up-to-date automatically.

## Installation

### 1. Prerequisites

Before installing, ensure you have the following dependencies on your system:

*   **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
*   **ffmpeg**: Essential for merging video segments.
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your system's PATH.
    *   **macOS**: `brew install ffmpeg`
    *   **Linux**: `sudo apt update && sudo apt install ffmpeg` (or use your distro's package manager).
*   **fzf**: Required for the interactive anime selection in the CLI.
    *   **Windows**: Download from the [fzf GitHub releases](https://github.com/junegunn/fzf/releases) and add to your PATH.
    *   **macOS**: `brew install fzf`
    *   **Linux**: `sudo apt update && sudo apt install fzf` (or use your distro's package manager).
*   **Node.js**: Required for an internal dependency.
    *   [Download Node.js](https://nodejs.org/en/download/) or use a package manager.

### 2. Install with uv (Recommended - Fast!)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install animepahe-dl
uv tool install animepahe-dl
```

### 3. Install with pip

```bash
pip install animepahe-dl
```

## Usage

The package can be run directly from your terminal.

### Command-Line Interface (CLI)

To run the CLI, use the `animepahe-dl` command:

```bash
# Search for an anime and select episodes interactively
animepahe-dl -n "Your Anime Name"

# Download specific episodes of an anime
animepahe-dl -n "Your Anime Name" -e 1 3 5
```

**CLI Options:**

| Flag | Alias | Description | Default |
|---|---|---|---|
| `--name` | `-n` | Name of the anime to search for. | |
| `--episodes` | `-e` | List or range of episode numbers (e.g., `1 2 5` or `1-10`). | |
| `--quality` | `-q` | Desired video quality (`best`, `1080`, `720`, `480`, `360`). | `best` |
| `--audio` | `-a` | Desired audio language (`eng` or `jpn`). | `jpn` |
| `--threads` | `-t` | Number of download threads for segments. | `100` |
| `--concurrent-downloads` | `-c` | Number of episodes to download concurrently. | `2` |
| `--updates` | | Check for new episodes of anime in your personal list. | |
| `--manage` | | Manage your personal anime list (add/remove anime). | |
| `--run-once` | | Use with `--updates` to run the check once and exit. | |
| `--insecure` | | Disable SSL certificate verification (not recommended). | |
| `--m3u8-only` | | Fetch playlist only without downloading segments. | |
| `--gui` | | Launch the Graphical User Interface. | |

**Examples:**

```bash
# Download episodes 1-10 with 720p quality
animepahe-dl -n "Naruto" -e 1-10 -q 720

# Download multiple episodes concurrently
animepahe-dl -n "Naruto" -e 1-20 -c 3 -t 150

# Download with English audio
animepahe-dl -n "Naruto" -e 1-5 -a eng

# Fetch playlist only (no download)
animepahe-dl -n "Naruto" -e 1 --m3u8-only
```


### Graphical User Interface (GUI)

To launch the GUI, use the `--gui` flag:

```bash
animepahe-dl --gui
```

The GUI provides a user-friendly interface for searching, selecting, and downloading anime without using the command line.

## Configuration

The application's configuration (`config.json`) and data files (`myanimelist.txt`, `animelist.txt`) are stored in your user data directory:

*   **Linux**: `~/.config/anime_downloader/`
*   **macOS**: `~/Library/Application Support/anime_downloader/`
*   **Windows**: `C:\Users\<YourUsername>\AppData\Local\anime_downloader\`

You can manually edit `config.json` to change defaults for quality, audio, threads, and the download directory.

## 🛠️ For Developers

### Development Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/ayushjaipuriyar/animepahe-dl.git
   cd animepahe-dl
   ```

3. **Install dependencies with uv:**
   ```bash
   uv sync --all-extras
   ```

   Or for development:
   ```bash
   uv sync --dev
   ```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=anime_downloader --cov-report=html

# Run specific test file
uv run pytest tests/test_cli.py -v
```

### Code Quality

```bash
# Format code
uv run black anime_downloader tests
uv run isort anime_downloader tests

# Lint code
uv run ruff check anime_downloader tests

# Type checking
uv run mypy anime_downloader

# Security scan
uv run bandit -r anime_downloader
```

### Project Structure

```
animepahe-dl/
├── anime_downloader/       # Main package
│   ├── api.py             # AnimePahe API client
│   ├── async_downloader.py # Async download implementation
│   ├── cache.py           # Caching system
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration management
│   ├── downloader.py      # Download orchestration
│   ├── gui.py             # PyQt6 GUI
│   ├── models.py          # Data models
│   ├── utils.py           # Utility functions
│   └── workers.py         # Background workers
├── tests/                 # Test suite
├── .github/workflows/     # CI/CD pipelines
└── pyproject.toml        # Project configuration
```

### Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Follow code style**: Use `black` and `isort` for formatting
3. **Write tests**: Maintain or improve code coverage
4. **Use Conventional Commits**: Follow the commit message format below
5. **Update documentation**: Keep README and docstrings current

#### Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automated releases:

- `feat:` New features (minor version bump)
- `fix:` Bug fixes (patch version bump)
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Test additions or modifications
- `chore:` Build process or auxiliary tool changes

Example:
```bash
git commit -m "feat: add async download support for improved performance"
git commit -m "fix: handle network timeout errors gracefully"
```

### Release Process

Releases are automated via GitHub Actions:
1. Push to `main` branch triggers semantic-release
2. Version is bumped based on commit messages
3. Changelog is generated automatically
4. Package is published to PyPI
5. GitHub release is created

## 📊 Performance Tips

- **Increase threads**: Use `-t 100` or higher for faster downloads
- **Concurrent episodes**: Use `-c 3` to download multiple episodes simultaneously
- **Quality selection**: Lower quality downloads faster (use `-q 720` instead of `1080`)
- **Cache management**: Regularly update cache with `--updates` for better performance

## 🐛 Troubleshooting

### Common Issues

**SSL Certificate Errors:**
```bash
animepahe-dl --insecure -n "Anime Name"
```

**FFmpeg not found:**
- Ensure ffmpeg is installed and in your PATH
- Set `FFMPEG` environment variable to ffmpeg binary path

**Cache issues:**
- Delete cache directory: `~/.config/anime_downloader/cache/`
- Update cache: Run with `--updates` flag

**Permission errors:**
- Check download directory permissions
- Run with appropriate user privileges

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes
- **[API Documentation](docs/API.md)** - Complete API reference
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute
- **[Security Policy](SECURITY.md)** - Security and vulnerability reporting
- **[Upgrade Guide](docs/UPGRADE_GUIDE.md)** - Version upgrade instructions
- **[UV Migration Guide](docs/UV_MIGRATION.md)** - Migrating to UV package manager
- **[Examples](examples/)** - Usage examples and scripts
- **[Benchmarks](benchmarks/)** - Performance benchmarks

## 🐳 Docker Support

Run animepahe-dl in a container:

```bash
# Build the image
docker build -t animepahe-dl .

# Run CLI
docker run -v ./downloads:/downloads animepahe-dl -n "Anime Name" -e 1-5

# Run with docker-compose
docker-compose up
```

See [docker-compose.yml](docker-compose.yml) for configuration options.

## 🔧 Advanced Usage

### Using as a Python Library

```python
from anime_downloader.api import AnimePaheAPI
from anime_downloader.downloader import Downloader

# Initialize
api = AnimePaheAPI(verify_ssl=False)
downloader = Downloader(api)

# Search for anime
results = api.search("Naruto")
print(results[0]['title'])

# Download episodes
# See examples/ directory for complete examples
```

### Automation with Cron

Check for new episodes automatically:

```bash
# Edit crontab
crontab -e

# Add this line (check every 6 hours)
0 */6 * * * /usr/local/bin/animepahe-dl --updates --run-once
```

### Environment Variables

- `FFMPEG` - Path to ffmpeg binary
- `XDG_CONFIG_HOME` - Config directory location
- `DOWNLOAD_DIR` - Default download directory

## 🚀 New Features in v5.2.1

- ⚡ **Async Downloads** - 2-3x faster with async/await
- 💾 **Smart Caching** - 50% reduction in API calls
- 📊 **Performance Monitoring** - Track download statistics
- 🔄 **Concurrent Episodes** - Download multiple episodes simultaneously
- 🐳 **Docker Support** - Easy containerized deployment
- 🧪 **Comprehensive Testing** - Full test suite with pytest
- 📝 **Type Hints** - Better IDE support and error detection
- 🛠️ **UV Support** - 10-100x faster dependency management

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

## 🙏 Acknowledgments

- AnimePahe for providing the content platform
- Contributors and users for feedback and improvements
- Open source community for the amazing tools and libraries
- [Astral](https://astral.sh/) for the amazing UV package manager

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect copyright laws and support official releases when available. The developers are not responsible for any misuse of this software.
