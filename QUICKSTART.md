# Quick Start Guide

Get up and running with animepahe-dl in 5 minutes!

## 🚀 Installation

### Prerequisites

Install these first:

**1. Python 3.8+**
```bash
python --version  # Should be 3.8 or higher
```

**2. FFmpeg**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

**3. fzf (for CLI)**
```bash
# macOS
brew install fzf

# Ubuntu/Debian
sudo apt install fzf

# Windows
# Download from https://github.com/junegunn/fzf/releases
```

**4. Node.js**
```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt install nodejs

# Windows
# Download from https://nodejs.org/
```

### Install animepahe-dl

**With uv (Recommended - Fast!):**
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install animepahe-dl
uv tool install animepahe-dl
```

**With pip:**
```bash
pip install animepahe-dl
```

## 📺 Basic Usage

### CLI - Interactive Mode

```bash
# Search and download interactively
animepahe-dl -n "Naruto"
```

This will:
1. Search for "Naruto"
2. Let you select the anime
3. Show available episodes
4. Let you choose which episodes to download

### CLI - Direct Download

```bash
# Download specific episodes
animepahe-dl -n "Naruto" -e 1 3 5

# Download episode range
animepahe-dl -n "Naruto" -e 1-10

# Download with custom quality
animepahe-dl -n "Naruto" -e 1-5 -q 720

# Download with English audio
animepahe-dl -n "Naruto" -e 1-5 -a eng
```

### GUI Mode

```bash
# Launch GUI
animepahe-dl --gui
```

## ⚙️ Configuration

Configuration file location:
- **Linux**: `~/.config/anime_downloader/config.json`
- **macOS**: `~/Library/Application Support/anime_downloader/config.json`
- **Windows**: `C:\Users\<YourUsername>\AppData\Local\anime_downloader\config.json`

### Default Configuration

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

### Customize Settings

Edit the config file or use the GUI settings dialog.

## 🎯 Common Tasks

### Download Entire Series

```bash
# Download all episodes
animepahe-dl -n "Death Note" -e 1-37
```

### Download Latest Episodes

```bash
# Check for new episodes
animepahe-dl --updates

# Run once and exit (for cron jobs)
animepahe-dl --updates --run-once
```

### Manage Your Anime List

```bash
# Manage your personal anime list
animepahe-dl --manage
```

### Fast Downloads

```bash
# Use more threads for faster downloads
animepahe-dl -n "Anime" -e 1-10 -t 100

# Download multiple episodes concurrently
animepahe-dl -n "Anime" -e 1-10 -c 3
```

### Lower Quality for Speed

```bash
# Download 720p instead of 1080p
animepahe-dl -n "Anime" -e 1-10 -q 720
```

## 🐳 Docker Usage

### Using Docker

```bash
# Pull image
docker pull animepahe-dl:latest

# Run CLI
docker run -v ./downloads:/downloads animepahe-dl -n "Naruto" -e 1-5

# Run GUI (requires X11)
docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix animepahe-dl --gui
```

### Using Docker Compose

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## 🔧 Troubleshooting

### SSL Certificate Errors

```bash
# Use insecure mode (not recommended)
animepahe-dl --insecure -n "Anime"
```

### FFmpeg Not Found

```bash
# Check if ffmpeg is installed
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows

# Add to PATH or set environment variable
export FFMPEG=/path/to/ffmpeg
```

### Slow Downloads

```bash
# Increase threads
animepahe-dl -n "Anime" -t 150

# Use lower quality
animepahe-dl -n "Anime" -q 720

# Download fewer episodes concurrently
animepahe-dl -n "Anime" -c 1
```

### Cache Issues

```bash
# Clear cache
rm -rf ~/.config/anime_downloader/cache/

# Update cache
animepahe-dl --updates --run-once
```

## 📚 Next Steps

### Learn More

- Read the [full README](README.md)
- Check [API documentation](docs/API.md)
- See [examples](examples/)
- Review [contributing guide](CONTRIBUTING.md)

### Advanced Usage

```bash
# Download with custom settings
animepahe-dl -n "Anime" -e 1-10 -q 1080 -a jpn -t 100 -c 2

# Fetch playlist only (no download)
animepahe-dl -n "Anime" -e 1 --m3u8-only

# Run in background
nohup animepahe-dl -n "Anime" -e 1-100 &
```

### Automation

Create a cron job to check for new episodes:

```bash
# Edit crontab
crontab -e

# Add this line (check every 6 hours)
0 */6 * * * /usr/local/bin/animepahe-dl --updates --run-once
```

### Python API

Use as a library:

```python
from anime_downloader.api import AnimePaheAPI
from anime_downloader.downloader import Downloader

api = AnimePaheAPI(verify_ssl=False)
downloader = Downloader(api)

# Search
results = api.search("Naruto")
print(results[0]['title'])

# Download
# ... (see examples/ directory)
```

## 💡 Tips

1. **Start with lower quality** (720p) to test
2. **Use concurrent downloads** for multiple episodes
3. **Increase threads** if you have fast internet
4. **Enable caching** to reduce API calls
5. **Check logs** if something goes wrong
6. **Update regularly** for bug fixes and features

## 🆘 Getting Help

- **Issues**: https://github.com/ayushjaipuriyar/animepahe-dl/issues
- **Discussions**: https://github.com/ayushjaipuriyar/animepahe-dl/discussions
- **Documentation**: https://github.com/ayushjaipuriyar/animepahe-dl#readme

## ⚠️ Disclaimer

This tool is for educational purposes only. Please respect copyright laws and support official releases when available.

---

**Happy downloading! 🎉**
