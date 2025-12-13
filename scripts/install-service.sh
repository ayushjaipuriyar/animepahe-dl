#!/bin/bash

# AnimePahe Downloader Service Installation Script
# This script installs the systemd service for AnimePahe Downloader

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root"
    print_status "Please run as a regular user with sudo privileges"
    exit 1
fi

# Check if systemd is available
if ! command -v systemctl &> /dev/null; then
    print_error "systemd is not available on this system"
    exit 1
fi

# Check if animepahe-dl is installed
if ! command -v animepahe-dl &> /dev/null; then
    print_error "animepahe-dl is not installed or not in PATH"
    print_status "Please install animepahe-dl first: pip install animepahe-dl"
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)

print_status "Installing AnimePahe Downloader systemd service..."
print_status "User: $CURRENT_USER"
print_status "Home: $USER_HOME"

# Create service file content with current user
SERVICE_CONTENT="[Unit]
Description=AnimePahe Downloader Daemon
After=network.target
Wants=network-online.target

[Service]
Type=forking
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$USER_HOME
ExecStart=$(which animepahe-dl) --daemon
ExecStop=/bin/kill -TERM \$MAINPID
ExecReload=/bin/kill -HUP \$MAINPID
PIDFile=$USER_HOME/.config/animepahe-dl/animepahe-dl.pid
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$USER_HOME/.config/animepahe-dl $USER_HOME/Videos
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target"

# Create temporary service file
TEMP_SERVICE_FILE="/tmp/animepahe-dl.service"
echo "$SERVICE_CONTENT" > "$TEMP_SERVICE_FILE"

# Install service file
print_status "Installing service file..."
sudo cp "$TEMP_SERVICE_FILE" /etc/systemd/system/animepahe-dl.service
sudo chown root:root /etc/systemd/system/animepahe-dl.service
sudo chmod 644 /etc/systemd/system/animepahe-dl.service

# Clean up temp file
rm "$TEMP_SERVICE_FILE"

# Reload systemd
print_status "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable service
print_status "Enabling service..."
sudo systemctl enable animepahe-dl.service

print_success "AnimePahe Downloader service installed successfully!"
print_status ""
print_status "Service management commands:"
print_status "  Start service:    sudo systemctl start animepahe-dl"
print_status "  Stop service:     sudo systemctl stop animepahe-dl"
print_status "  Restart service:  sudo systemctl restart animepahe-dl"
print_status "  Check status:     sudo systemctl status animepahe-dl"
print_status "  View logs:        sudo journalctl -u animepahe-dl -f"
print_status "  Disable service:  sudo systemctl disable animepahe-dl"
print_status ""
print_warning "Make sure to configure your anime list before starting the service:"
print_status "  animepahe-dl --manage"
print_status ""
print_status "To start the service now, run:"
print_status "  sudo systemctl start animepahe-dl"