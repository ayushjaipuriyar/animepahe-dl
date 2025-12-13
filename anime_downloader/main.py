#!/usr/bin/python3
"""
Main entry point for the AnimePahe Downloader.

This script acts as a dispatcher, deciding whether to launch the command-line
interface (CLI) or the graphical user interface (GUI) based on the
command-line arguments provided.
"""

import sys
import argparse
from .utils import constants, config_manager, logger


def main():
    """
    Parses a single `--gui` argument to decide which interface to run.

    This function uses a pre-parser to check for the `--gui` flag without
    interfering with the argument parsing of the full CLI application.
    """
    # A pre-parser to check only for the --gui flag.
    # `add_help=False` prevents it from conflicting with the main parser's -h flag.
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--gui", action="store_true", help="Launch the graphical user interface."
    )

    # `parse_known_args` separates the --gui flag from the rest of the arguments.
    pre_args, remaining_args = pre_parser.parse_known_args()

    # Load user config early, apply base_url if overridden
    try:
        user_cfg = config_manager.load_config()
        if "base_url" in user_cfg and user_cfg["base_url"] != constants.get_base_url():
            constants.set_base_url(user_cfg["base_url"])
    except Exception as e:
        logger.warning(f"Failed to load config early: {e}")

    if pre_args.gui:
        logger.info("Launching GUI...")
        # Dynamically import the GUI to avoid loading PyQt6 unless necessary.
        from .gui import run_gui

        # We reconstruct sys.argv to pass only the remaining arguments to the GUI.
        # This prevents PyQt from misinterpreting arguments meant for the CLI.
        sys.argv = [sys.argv[0]] + remaining_args
        run_gui()
    else:
        # If --gui is not present, import and run the CLI.
        # The CLI will handle its own full argument parsing.
        from .cli import cli_main

        cli_main()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"An unexpected error occurred: {e}")
        logger.exception("Traceback:")
        sys.exit(1)
