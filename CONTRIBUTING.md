# Contributing to AnimePahe Downloader

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- FFmpeg (for testing download functionality)
- Node.js (for certain features)

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/animepahe-dl.git
   cd animepahe-dl
   ```

3. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

4. Install dependencies:
   ```bash
   uv sync --dev --all-extras
   ```

5. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Making Changes

1. **Write code** following the project's style guidelines
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Run tests** to ensure nothing breaks
5. **Commit changes** using conventional commit format

### Code Style

We use automated tools to maintain code quality:

```bash
# Format code
uv run black anime_downloader tests
uv run isort anime_downloader tests

# Check linting
uv run ruff check anime_downloader tests

# Type checking
uv run mypy anime_downloader --ignore-missing-imports
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=anime_downloader --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_cli.py -v

# Run tests matching a pattern
uv run pytest -k "test_episode"
```

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes
- `ci`: CI/CD changes

**Examples:**
```bash
feat(cli): add support for episode range selection
fix(downloader): handle network timeout errors
docs(readme): update installation instructions
test(api): add tests for search functionality
```

## Pull Request Process

1. **Update documentation** if you've changed APIs or added features
2. **Add tests** for new functionality
3. **Ensure all tests pass** locally
4. **Update CHANGELOG.md** if applicable
5. **Push to your fork** and submit a pull request
6. **Request review** from maintainers

### Pull Request Checklist

- [ ] Code follows the project's style guidelines
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated
- [ ] Commit messages follow conventional commits
- [ ] No merge conflicts with main branch
- [ ] PR description clearly explains the changes

## Types of Contributions

### Bug Reports

When filing a bug report, include:
- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages or logs
- Screenshots if applicable

### Feature Requests

When suggesting a feature:
- Explain the use case
- Describe the proposed solution
- Consider alternative solutions
- Discuss potential drawbacks

### Code Contributions

Areas where contributions are welcome:
- Bug fixes
- New features
- Performance improvements
- Documentation improvements
- Test coverage improvements
- Code refactoring

### Documentation

Documentation improvements are always welcome:
- Fix typos or clarify existing docs
- Add examples and tutorials
- Improve API documentation
- Translate documentation

## Project Structure

```
animepahe-dl/
├── anime_downloader/          # Main package
│   ├── __init__.py
│   ├── api.py                # API client
│   ├── async_downloader.py   # Async downloads
│   ├── cache.py              # Caching system
│   ├── cli.py                # CLI interface
│   ├── config.py             # Configuration
│   ├── config_manager.py     # Config management
│   ├── downloader.py         # Download logic
│   ├── gui.py                # GUI interface
│   ├── helper.py             # Helper functions
│   ├── logger.py             # Logging setup
│   ├── main.py               # Entry point
│   ├── models.py             # Data models
│   ├── utils.py              # Utilities
│   └── workers.py            # Background workers
├── tests/                     # Test suite
│   ├── conftest.py           # Pytest fixtures
│   ├── test_cli.py
│   ├── test_config_manager.py
│   ├── test_helper.py
│   └── test_models.py
├── .github/                   # GitHub configuration
│   ├── workflows/            # CI/CD workflows
│   └── dependabot.yml        # Dependency updates
├── pyproject.toml            # Project configuration
├── README.md                 # Main documentation
├── CONTRIBUTING.md           # This file
├── CHANGELOG.md              # Version history
└── LICENSE                   # MIT License
```

## Development Tips

### Running Locally

```bash
# Run CLI
python -m anime_downloader.main -n "Anime Name"

# Run GUI
python -m anime_downloader.main --gui

# Run with debugging
python -m pdb -m anime_downloader.main -n "Anime Name"
```

### Debugging

- Use `logger.debug()` for detailed logging
- Set breakpoints with `import pdb; pdb.set_trace()`
- Check logs in `~/.config/anime_downloader/`

### Performance Profiling

```bash
# Profile code
python -m cProfile -o profile.stats -m anime_downloader.main -n "Anime"

# View results
python -m pstats profile.stats
```

## Questions?

- Open an issue for questions
- Check existing issues and discussions
- Reach out to maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
