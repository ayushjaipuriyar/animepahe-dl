#!/usr/bin/env python3
"""
Example script demonstrating background monitoring and notification features.

This script shows how to use the new background monitoring, daemon mode,
and notification features of animepahe-dl.
"""

import time
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and print the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✓ Success!")
            if result.stdout:
                print("Output:", result.stdout.strip())
        else:
            print("✗ Failed!")
            if result.stderr:
                print("Error:", result.stderr.strip())
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("✗ Command timed out!")
        return False
    except Exception as e:
        print(f"✗ Error running command: {e}")
        return False

def main():
    """Demonstrate background monitoring features."""
    print("AnimePahe Downloader - Background Monitoring Demo")
    print("=" * 60)
    
    # Check if animepahe-dl is available
    if not run_command(["python", "-m", "anime_downloader.main", "--help"], 
                      "Checking if animepahe-dl is available"):
        print("Please install animepahe-dl first!")
        sys.exit(1)
    
    print("\n🔔 NOTIFICATION FEATURES:")
    print("- Desktop notifications are now enabled by default")
    print("- You'll get notified when downloads complete")
    print("- Background monitoring sends notifications for new episodes")
    
    print("\n🖥️ SYSTEM TRAY FEATURES (GUI only):")
    print("- Launch GUI with: animepahe-dl --gui")
    print("- Close button minimizes to system tray")
    print("- Right-click tray icon for quick actions")
    print("- Toggle background monitoring from tray menu")
    
    print("\n🔄 DAEMON MODE FEATURES:")
    print("Available daemon commands:")
    
    # Show daemon help
    run_command(["python", "-m", "anime_downloader.main", "--daemon-action", "status"], 
               "Check daemon status")
    
    print("\n📋 EXAMPLE WORKFLOWS:")
    
    print("\n1. Setup for background monitoring:")
    print("   animepahe-dl --manage  # Add anime to your watchlist")
    print("   animepahe-dl --daemon  # Start background monitoring")
    
    print("\n2. Manual daemon management:")
    print("   animepahe-dl --daemon-action start")
    print("   animepahe-dl --daemon-action status")
    print("   animepahe-dl --daemon-action stop")
    
    print("\n3. Linux service installation:")
    print("   ./scripts/install-service.sh")
    print("   sudo systemctl start animepahe-dl")
    print("   sudo systemctl enable animepahe-dl")
    
    print("\n4. GUI with system tray:")
    print("   animepahe-dl --gui")
    print("   # Use tray menu to toggle background monitoring")
    
    print("\n🎮 STREAMING FEATURES:")
    print("   animepahe-dl -n 'Anime Name' -e 1-5 --play")
    print("   animepahe-dl -n 'Anime Name' -e 1 --play --player mpv")
    
    print("\n📁 CONFIGURATION:")
    config_path = Path.home() / ".config" / "animepahe-dl" / "config.json"
    print(f"   Configuration file: {config_path}")
    print("   Edit to customize update intervals, quality, etc.")
    
    print("\n🔍 MONITORING:")
    log_path = Path.home() / ".config" / "animepahe-dl" / "daemon.log"
    print(f"   Daemon logs: {log_path}")
    print("   System logs: sudo journalctl -u animepahe-dl -f")
    
    print("\n" + "="*60)
    print("Demo completed! Try the commands above to explore the features.")
    print("="*60)

if __name__ == "__main__":
    main()