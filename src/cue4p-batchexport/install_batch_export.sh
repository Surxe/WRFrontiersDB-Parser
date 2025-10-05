#!/bin/bash

# Download CUE4P BatchExport v1.0.0 Windows release
# This script downloads the Windows x64 release of BatchExport from GitHub

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATCH_EXPORT_DIR="$SCRIPT_DIR"
VERSION="v1.0.0"
RELEASE_URL="https://github.com/Surxe/CUE4P-BatchExport/releases/download/${VERSION}/BatchExport-${VERSION}-win-x64.zip"
ZIP_FILE="BatchExport-${VERSION}-win-x64.zip"
EXECUTABLE_NAME="BatchExport.exe"

echo "================================================"
echo "CUE4P BatchExport Installer"
echo "================================================"
echo "Version: $VERSION"
echo "Target Directory: $BATCH_EXPORT_DIR"
echo "Download URL: $RELEASE_URL"
echo ""

# Check if BatchExport is already installed
if [ -f "$BATCH_EXPORT_DIR/$EXECUTABLE_NAME" ]; then
    echo "✓ BatchExport executable already exists at: $BATCH_EXPORT_DIR/$EXECUTABLE_NAME"
    echo "To reinstall, delete the executable and run this script again."
    exit 0
fi

# Check if curl or wget is available
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD_CMD="curl -L -o"
    echo "Using curl for download..."
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD_CMD="wget -O"
    echo "Using wget for download..."
else
    echo "❌ Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Download the release zip file
echo "📦 Downloading BatchExport $VERSION..."
cd "$BATCH_EXPORT_DIR"

if [ "$DOWNLOAD_CMD" = "curl -L -o" ]; then
    curl -L -o "$ZIP_FILE" "$RELEASE_URL"
else
    wget -O "$ZIP_FILE" "$RELEASE_URL"
fi

# Check if download was successful
if [ ! -f "$ZIP_FILE" ]; then
    echo "❌ Error: Failed to download $ZIP_FILE"
    exit 1
fi

echo "✓ Downloaded $ZIP_FILE"

# Check if unzip is available
if ! command -v unzip >/dev/null 2>&1; then
    echo "❌ Error: unzip not found. Please install unzip to extract the archive."
    exit 1
fi

# Extract the zip file
echo "📂 Extracting BatchExport..."
unzip -o "$ZIP_FILE"

# Find and move the executable to the current directory
EXTRACTED_EXECUTABLE=""
if [ -f "$EXECUTABLE_NAME" ]; then
    EXTRACTED_EXECUTABLE="$EXECUTABLE_NAME"
elif [ -f "win-x64/$EXECUTABLE_NAME" ]; then
    EXTRACTED_EXECUTABLE="win-x64/$EXECUTABLE_NAME"
    mv "win-x64/$EXECUTABLE_NAME" "$EXECUTABLE_NAME"
    rmdir "win-x64" 2>/dev/null || true
else
    # Search for the executable in any subdirectory
    FOUND_EXECUTABLE=$(find . -name "$EXECUTABLE_NAME" -type f | head -n 1)
    if [ -n "$FOUND_EXECUTABLE" ]; then
        EXTRACTED_EXECUTABLE="$FOUND_EXECUTABLE"
        mv "$FOUND_EXECUTABLE" "$EXECUTABLE_NAME"
        # Clean up any empty directories
        find . -type d -empty -delete 2>/dev/null || true
    fi
fi

# Verify extraction was successful
if [ ! -f "$EXECUTABLE_NAME" ]; then
    echo "❌ Error: $EXECUTABLE_NAME not found after extraction"
    echo "Contents of extracted files:"
    ls -la
    exit 1
fi

# Clean up zip file
rm -f "$ZIP_FILE"

# Clean up any remaining extracted directories if they're empty
find . -name "win-x64" -type d -empty -delete 2>/dev/null || true
find . -name "*x64*" -type d -empty -delete 2>/dev/null || true

echo "✓ Extracted and cleaned up"

# Verify the executable
echo "🔍 Verifying BatchExport installation..."
if [ -f "$EXECUTABLE_NAME" ]; then
    FILE_SIZE=$(stat -f%z "$EXECUTABLE_NAME" 2>/dev/null || stat -c%s "$EXECUTABLE_NAME" 2>/dev/null || echo "unknown")
    echo "✓ BatchExport executable found"
    echo "  Path: $BATCH_EXPORT_DIR/$EXECUTABLE_NAME"
    echo "  Size: $FILE_SIZE bytes"
    
    # Make executable (in case we're on WSL or similar)
    chmod +x "$EXECUTABLE_NAME" 2>/dev/null || true
    
    echo ""
    echo "🎉 BatchExport $VERSION installed successfully!"
    echo ""
    echo "Usage:"
    echo "  $BATCH_EXPORT_DIR/$EXECUTABLE_NAME [options]"
    echo ""
    echo "To use from Python:"
    echo "  executable_path = r'$BATCH_EXPORT_DIR\\$EXECUTABLE_NAME'"
    
else
    echo "❌ Error: Installation verification failed"
    exit 1
fi

echo "================================================"
echo "Installation Complete"
echo "================================================"
