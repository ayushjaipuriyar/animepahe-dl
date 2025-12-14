#!/bin/bash
set -e

# Build Flatpak for animepahe-dl
# This script should be run in a Flatpak build environment

MANIFEST="com.github.ayushjaipuriyar.animepahe-dl.yml"
APP_ID="com.github.ayushjaipuriyar.animepahe-dl"
REPO_DIR="flatpak-repo"
BUILD_DIR="flatpak-build"

echo "Building Flatpak for AnimePahe Downloader..."

# Clean previous builds
rm -rf "$BUILD_DIR" "$REPO_DIR"

# Initialize repo
flatpak-builder --repo="$REPO_DIR" "$BUILD_DIR" "$MANIFEST" --force-clean

# Create bundle
flatpak build-bundle "$REPO_DIR" "${APP_ID}.flatpak" "$APP_ID"

echo "Flatpak bundle created: ${APP_ID}.flatpak"