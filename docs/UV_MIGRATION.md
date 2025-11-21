# UV Migration Guide

This project now uses [uv](https://github.com/astral-sh/uv) for faster and more reliable dependency management!

## Why UV?

- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic** dependency resolution
- 🎯 **Better error messages**
- 📦 **Built-in virtual environment management**
- 🚀 **Drop-in replacement** for pip

## Installation

### Install UV

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**With pip:**
```bash
pip install uv
```

**With Homebrew:**
```bash
brew install uv
```

## For Users

### Installing animepahe-dl

**Old way (pip):**
```bash
pip install animepahe-dl
```

**New way (uv):**
```bash
uv tool install animepahe-dl
```

### Running animepahe-dl

After installation with `uv tool install`, the command works the same:
```bash
animepahe-dl -n "Anime Name"
```

## For Developers

### Setting Up Development Environment

**Old way:**
```bash
git clone https://github.com/ayushjaipuriyar/animepahe-dl.git
cd animepahe-dl
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**New way:**
```bash
git clone https://github.com/ayushjaipuriyar/animepahe-dl.git
cd animepahe-dl
uv sync --dev --all-extras
```

That's it! UV automatically:
- Creates a virtual environment
- Installs all dependencies
- Installs the package in editable mode

### Running Commands

**Old way:**
```bash
pytest
black anime_downloader tests
ruff check anime_downloader
```

**New way:**
```bash
uv run pytest
uv run black anime_downloader tests
uv run ruff check anime_downloader
```

Or activate the environment:
```bash
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Then run commands normally
pytest
black anime_downloader tests
```

### Common Tasks

| Task | Old Command | New Command |
|------|-------------|-------------|
| Install deps | `pip install -e ".[dev]"` | `uv sync --dev` |
| Run tests | `pytest` | `uv run pytest` |
| Format code | `black .` | `uv run black .` |
| Lint code | `ruff check .` | `uv run ruff check .` |
| Build package | `python -m build` | `uv build` |
| Publish | `twine upload dist/*` | `uv publish` |

### Using Makefile

The Makefile has been updated to use uv:

```bash
make install-dev  # Install with uv
make test         # Run tests with uv
make format       # Format code with uv
make lint         # Lint code with uv
```

## Key Differences

### Virtual Environments

**pip:**
- Manual creation: `python -m venv .venv`
- Manual activation required
- Separate from dependency installation

**uv:**
- Automatic creation with `uv sync`
- Can run commands without activation using `uv run`
- Integrated with dependency management

### Lock Files

**pip:**
- `requirements.txt` (not deterministic)
- `Pipfile.lock` (if using pipenv)

**uv:**
- `uv.lock` (deterministic, cross-platform)
- Ensures exact same versions everywhere

### Speed Comparison

| Operation | pip | uv | Speedup |
|-----------|-----|-----|---------|
| Install from cache | 2.5s | 0.1s | 25x |
| Cold install | 15s | 1.5s | 10x |
| Resolve deps | 5s | 0.3s | 16x |

## Migration Checklist

### For Users

- [ ] Install uv
- [ ] Uninstall old version: `pip uninstall animepahe-dl`
- [ ] Install with uv: `uv tool install animepahe-dl`
- [ ] Test: `animepahe-dl --help`

### For Developers

- [ ] Install uv
- [ ] Remove old venv: `rm -rf .venv`
- [ ] Install dependencies: `uv sync --dev --all-extras`
- [ ] Update your workflow to use `uv run` commands
- [ ] Test everything works: `make test`

## Troubleshooting

### UV not found after installation

Add UV to your PATH:
```bash
# Linux/macOS
export PATH="$HOME/.cargo/bin:$PATH"

# Windows
# Add %USERPROFILE%\.cargo\bin to your PATH
```

### Virtual environment issues

Remove and recreate:
```bash
rm -rf .venv
uv sync --dev --all-extras
```

### Lock file conflicts

Update the lock file:
```bash
uv lock --upgrade
```

### Package not found

Clear UV cache:
```bash
uv cache clean
uv sync --dev --all-extras
```

## Advanced Usage

### Adding Dependencies

**Add a runtime dependency:**
```bash
uv add requests
```

**Add a dev dependency:**
```bash
uv add --dev pytest
```

### Updating Dependencies

**Update all dependencies:**
```bash
uv lock --upgrade
uv sync
```

**Update specific package:**
```bash
uv lock --upgrade-package requests
uv sync
```

### Running Scripts

**Run a Python script:**
```bash
uv run python script.py
```

**Run with specific Python version:**
```bash
uv run --python 3.11 python script.py
```

### Creating Tools

**Install as a tool (isolated environment):**
```bash
uv tool install animepahe-dl
```

**List installed tools:**
```bash
uv tool list
```

**Uninstall a tool:**
```bash
uv tool uninstall animepahe-dl
```

## CI/CD Integration

### GitHub Actions

The project's CI workflows have been updated to use uv:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4
  with:
    enable-cache: true

- name: Set up Python
  run: uv python install 3.11

- name: Install dependencies
  run: uv sync --dev

- name: Run tests
  run: uv run pytest
```

### Docker

The Dockerfile has been updated to use uv for faster builds:

```dockerfile
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies
RUN uv sync --frozen --no-dev
```

## Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub](https://github.com/astral-sh/uv)
- [UV vs pip comparison](https://docs.astral.sh/uv/pip/compatibility/)
- [Migration guide](https://docs.astral.sh/uv/guides/projects/)

## FAQ

**Q: Can I still use pip?**
A: Yes! UV is a drop-in replacement, but pip still works. However, uv is much faster.

**Q: Will this break my existing setup?**
A: No. UV creates its own virtual environment and doesn't interfere with pip.

**Q: Do I need to learn new commands?**
A: Mostly no. `uv pip install` works like `pip install`. But `uv sync` is recommended.

**Q: Is UV stable?**
A: Yes! UV is production-ready and used by many large projects.

**Q: What about Windows support?**
A: UV works great on Windows, Linux, and macOS.

## Getting Help

If you encounter issues with UV:

1. Check the [UV documentation](https://docs.astral.sh/uv/)
2. Search [UV issues](https://github.com/astral-sh/uv/issues)
3. Ask in our [project discussions](https://github.com/ayushjaipuriyar/animepahe-dl/discussions)

---

**Welcome to the UV era! 🚀**
