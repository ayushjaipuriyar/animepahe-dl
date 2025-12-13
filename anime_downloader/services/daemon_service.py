"""
Daemon service for running animepahe-dl as a background service.

This module provides functionality to run the anime downloader as a daemon
process that continuously monitors for new episodes and downloads them.
"""

import os
import sys
import time
import signal
import atexit
import logging
from pathlib import Path
from typing import Optional

from ..utils import constants, config_manager
from ..utils.logger import logger
from ..api import AnimePaheAPI, Downloader
from ..cli.commands import run_update_check
from plyer import notification


class DaemonService:
    """
    A daemon service that runs in the background to monitor and download new episodes.
    """
    
    def __init__(self, pidfile: str = None):
        self.pidfile = pidfile or os.path.join(constants.BASE_DATA_DIR, "animepahe-dl.pid")
        self.api = None
        self.downloader = None
        self.running = False
        
    def daemonize(self):
        """
        Daemonize the current process using the double-fork technique.
        """
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)
        
        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # Exit second parent
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Create log file for daemon output
        log_file = os.path.join(constants.BASE_DATA_DIR, "daemon.log")
        
        with open('/dev/null', 'r') as si:
            os.dup2(si.fileno(), sys.stdin.fileno())
        with open(log_file, 'a+') as so:
            os.dup2(so.fileno(), sys.stdout.fileno())
        with open(log_file, 'a+') as se:
            os.dup2(se.fileno(), sys.stderr.fileno())
        
        # Write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as f:
            f.write(f"{pid}\n")
    
    def delpid(self):
        """Remove the PID file."""
        try:
            os.remove(self.pidfile)
        except OSError:
            pass
    
    def start(self):
        """
        Start the daemon.
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            pid = None
        
        if pid:
            # Check if process is actually running
            try:
                os.kill(pid, 0)
                logger.error(f"Daemon already running with PID {pid}")
                sys.exit(1)
            except OSError:
                # Process not running, remove stale pidfile
                os.remove(self.pidfile)
        
        # Start the daemon
        logger.info("Starting animepahe-dl daemon...")
        self.daemonize()
        self.run()
    
    def stop(self):
        """
        Stop the daemon.
        """
        # Get the pid from the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            pid = None
        
        if not pid:
            logger.error("Daemon not running (no pidfile found)")
            return
        
        # Try killing the daemon process
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            if "No such process" in str(err):
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                logger.info("Daemon stopped successfully")
            else:
                logger.error(f"Failed to stop daemon: {err}")
                sys.exit(1)
    
    def restart(self):
        """
        Restart the daemon.
        """
        self.stop()
        time.sleep(1)
        self.start()
    
    def status(self):
        """
        Check daemon status.
        """
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            logger.info("Daemon is not running")
            return False
        
        try:
            os.kill(pid, 0)
            logger.info(f"Daemon is running with PID {pid}")
            return True
        except OSError:
            logger.info("Daemon is not running (stale pidfile)")
            os.remove(self.pidfile)
            return False
    
    def run(self):
        """
        Main daemon loop.
        """
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Initialize API and downloader
        app_config = config_manager.load_config()
        if "base_url" in app_config and app_config["base_url"] != constants.get_base_url():
            constants.set_base_url(app_config["base_url"])
        
        self.api = AnimePaheAPI(verify_ssl=False)
        self.downloader = Downloader(self.api)
        
        # Create a mock args object for run_update_check
        class MockArgs:
            def __init__(self, config):
                self.quality = config.get("quality", "best")
                self.audio = config.get("audio", "jpn")
                self.threads = config.get("threads", 100)
                self.concurrent_downloads = config.get("concurrent_downloads", 2)
                self.run_once = False
                self.verbose = False
        
        args = MockArgs(app_config)
        
        # Send startup notification
        try:
            notification.notify(
                title="Animepahe-dl Daemon",
                message="Background service started - monitoring for new episodes",
                app_name="Animepahe Downloader",
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")
        
        logger.info("Daemon started successfully")
        logger.info(f"Update interval: {constants.UPDATE_CHECK_INTERVAL_MINUTES} minutes")
        
        # Main daemon loop
        while self.running:
            try:
                logger.info("Running update check...")
                run_update_check(self.api, self.downloader, args, app_config)
                
                # Wait for next check
                for _ in range(constants.UPDATE_CHECK_INTERVAL_MINUTES * 60):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                try:
                    notification.notify(
                        title="Animepahe-dl Daemon Error",
                        message=f"Daemon encountered an error: {str(e)[:100]}",
                        app_name="Animepahe Downloader",
                        timeout=15
                    )
                except Exception:
                    pass
                
                # Wait before retrying
                time.sleep(60)
        
        logger.info("Daemon shutting down...")
        
        # Send shutdown notification
        try:
            notification.notify(
                title="Animepahe-dl Daemon",
                message="Background service stopped",
                app_name="Animepahe Downloader",
                timeout=10
            )
        except Exception:
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


def run_daemon_command(action: str, pidfile: Optional[str] = None):
    """
    Run daemon commands (start, stop, restart, status).
    
    Args:
        action: The action to perform (start, stop, restart, status)
        pidfile: Optional custom PID file path
    """
    daemon = DaemonService(pidfile)
    
    if action == "start":
        daemon.start()
    elif action == "stop":
        daemon.stop()
    elif action == "restart":
        daemon.restart()
    elif action == "status":
        daemon.status()
    else:
        logger.error(f"Unknown daemon action: {action}")
        logger.info("Available actions: start, stop, restart, status")
        sys.exit(1)