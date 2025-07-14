"""
This module configures a centralized logger for the entire application.

It uses the `loguru` library to provide a simple, powerful, and "pretty"
logging experience out of the box. The logger is pre-configured with a
format that includes timestamps, log levels, and colors for readability.

To use the logger in any module, simply import it:
`from logger import logger`
"""

import sys
from loguru import logger

# Remove the default handler to prevent duplicate outputs
logger.remove()

# Configure a new handler with a custom format and colors
logger.add(
    sys.stderr,
    level="INFO",
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# You can optionally add a file logger for persistent logs
# logger.add(
#     "logs/app.log",
#     level="DEBUG",
#     rotation="10 MB",
#     retention="7 days",
#     format="{time} {level} {message}",
#     enqueue=True,
#     backtrace=True,
#     diagnose=True,
# )