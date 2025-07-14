# AnimePahe Downloader

A Python-based tool to download anime from AnimePahe, featuring both a Command-Line Interface (CLI) and a Graphical User Interface (GUI).

## Features

*   Search for anime on AnimePahe.
*   Download individual episodes or entire series.
*   Resume interrupted downloads.
*   Cross-platform compatibility (Windows, macOS, Linux).
*   Desktop notifications upon download completion.
*   Automatic cache updates for anime lists.

## Installation

### Prerequisites

Before installing, ensure you have the following tools installed on your system:

*   **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
*   **pipenv**: Install with `pip install pipenv`
*   **ffmpeg**: Essential for compiling video segments.
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to your PATH.
    *   **macOS**: `brew install ffmpeg` (using Homebrew)
    *   **Linux**: `sudo apt update && sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg` (Fedora), etc.
*   **fzf**: Used for interactive selection in the CLI.
    *   **Windows**: Download from [fzf GitHub](https://github.com/junegunn/fzf/releases) and add to your PATH.
    *   **macOS**: `brew install fzf` (using Homebrew)
    *   **Linux**: `sudo apt update && sudo apt install fzf` (Debian/Ubuntu), `sudo dnf install fzf` (Fedora), etc.
*   **Node.js**: Required for some internal processes.
    *   [Download Node.js](https://nodejs.org/en/download/) or use a package manager (`brew install node`, `sudo apt install nodejs`).

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/anime_downloader.git
    cd anime_downloader
    ```
    *(Note: Replace `https://github.com/your-username/anime_downloader.git` with the actual repository URL if you've forked it.)*

2.  **Install dependencies using pipenv:**
    ```bash
    pipenv install
    ```
    This will create a virtual environment and install all required Python packages.

## Usage

### Command-Line Interface (CLI)

To run the CLI, activate the pipenv shell and execute `main.py`:

```bash
pipenv run python main.py -n "Your Anime Name"
```

Replace `"Your Anime Name"` with the title of the anime you want to search for.

**CLI Options:**

*   `-n`, `--name`: Name of the anime to search for.
*   `-e`, `--episodes`: List of episode numbers to download (e.g., `1 2 5`).
*   `-q`, `--quality`: Desired video quality (e.g., `720`, `1080`). Default: `1080`.
*   `-a`, `--audio`: Desired audio language (`eng` or `jpn`). Default: `jpn`.
*   `-t`, `--threads`: Number of download threads. Default: `100`.
*   `--updates`: Check for new episodes of anime in your personal list.
*   `--manage`: Manage your personal anime list (add/remove anime).
*   `--run-once`: Use with `--updates` to run the update check once and exit (useful for cron jobs).

### Graphical User Interface (GUI)

To launch the GUI:

```bash
pipenv run python main.py --gui
```

The GUI provides a user-friendly interface for searching, selecting, and downloading anime.

## Configuration

The application's configuration (`config.json`) and data files (`myanimelist.txt`, `animelist.txt`) are stored in standard user data directories:

*   **Linux**: `~/.config/anime_downloader/`
*   **macOS**: `~/Library/Application Support/anime_downloader/`
*   **Windows**: `C:\Users\<YourUsername>\AppData\Local\anime_downloader\`

You can manually edit `config.json` to change default quality, audio, threads, and download directory.