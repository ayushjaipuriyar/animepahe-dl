# AnimePahe Downloader

[![PyPI version](https://badge.fury.io/py/animepahe-dl.svg)](https://badge.fury.io/py/animepahe-dl)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/release.yml/badge.svg)](https://github.com/ayushjaipuriyar/animepahe-dl/actions/workflows/release.yml)

A Python-based tool to download anime from AnimePahe, featuring both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

![Screenshot](ss1.png)

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

### 2. Install with pip

Once the prerequisites are installed, you can install the downloader from PyPI:

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
| `--episodes` | `-e` | List of episode numbers to download (e.g., `1 2 5`). | |
| `--quality` | `-q` | Desired video quality (`720` or `1080`). | `1080` |
| `--audio` | `-a` | Desired audio language (`eng` or `jpn`). | `jpn` |
| `--threads` | `-t` | Number of download threads. | `100` |
| `--updates` | | Check for new episodes of anime in your personal list. | |
| `--manage` | | Manage your personal anime list (add/remove anime). | |
| `--run-once` | | Use with `--updates` to run the check once and exit. | |
| `--gui` | | Launch the Graphical User Interface. | |


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

## For Developers

If you want to contribute to the project, you can install it from the source.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ayushjaipuriyar/animepahe-dl.git
    cd animepahe-dl
    ```

2.  **Install dependencies using pipenv:**
    ```bash
    pip install pipenv
    pipenv install --dev
    ```
    This will create a virtual environment and install all required packages.

### Conventional Commits

This project uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for release automation. When creating a pull request, please make sure your commit messages follow the standard.

*   `feat:` for new features (triggers a minor version bump).
*   `fix:` for bug fixes (triggers a patch version bump).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
