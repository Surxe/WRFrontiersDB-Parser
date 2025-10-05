#!/bin/bash

# Download CUE4P BatchExport latest Windows release
# This script downloads the latest Windows x64 release of BatchExport from GitHub

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BATCH_EXPORT_DIR="$SCRIPT_DIR/BatchExport"
EXECUTABLE_NAME="BatchExport.exe"

# Create the BatchExport directory if it doesn't exist
mkdir -p "$BATCH_EXPORT_DIR"

# Get latest version from GitHub API
echo "Fetching latest version from GitHub..."
LATEST_RELEASE_API="https://api.github.com/repos/Surxe/CUE4P-BatchExport/releases/latest"

# Try to get latest version using curl or wget
if command -v curl >/dev/null 2>&1; then
    VERSION=$(curl -s "$LATEST_RELEASE_API" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
elif command -v wget >/dev/null 2>&1; then
    VERSION=$(wget -qO- "$LATEST_RELEASE_API" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
else
    echo "Error: Neither curl nor wget found for API call. Falling back to v1.0.0"
    VERSION="v1.0.0"
fi

# Fallback if API call failed
if [ -z "$VERSION" ] || [ "$VERSION" = "null" ]; then
    echo "Warning: Failed to get latest version from API. Using v1.0.0"
    VERSION="v1.0.0"
fi

echo "Detected version: $VERSION"

# Use the correct asset name from GitHub releases
RELEASE_URL="https://github.com/Surxe/CUE4P-BatchExport/releases/download/${VERSION}/BatchExport-windows-x64.zip"
ZIP_FILE="BatchExport-windows-x64.zip"

echo "================================================"
echo "CUE4P BatchExport Installer"
echo "================================================"
echo "Version: $VERSION"
echo "Target Directory: $BATCH_EXPORT_DIR"
echo "Download URL: $RELEASE_URL"
echo ""

# Check if BatchExport is already installed
if [ -f "$BATCH_EXPORT_DIR/$EXECUTABLE_NAME" ]; then
    echo "BatchExport executable already exists at: $BATCH_EXPORT_DIR/$EXECUTABLE_NAME"
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
    echo "Error: Neither curl nor wget found. Please install one of them."
    exit 1
fi

# Download the release zip file
echo "Downloading BatchExport $VERSION..."
cd "$BATCH_EXPORT_DIR"

if [ "$DOWNLOAD_CMD" = "curl -L -o" ]; then
    curl -L -o "$ZIP_FILE" "$RELEASE_URL"
else
    wget -O "$ZIP_FILE" "$RELEASE_URL"
fi

# Check if download was successful
if [ ! -f "$ZIP_FILE" ]; then
    echo "Error: Failed to download $ZIP_FILE"
    exit 1
fi

# Validate the downloaded file
FILE_SIZE=$(stat -f%z "$ZIP_FILE" 2>/dev/null || stat -c%s "$ZIP_FILE" 2>/dev/null || echo "0")
echo "Downloaded $ZIP_FILE (Size: $FILE_SIZE bytes)"

# Check if file is too small (likely an error page)
if [ "$FILE_SIZE" -lt 1000 ]; then
    echo "Error: Downloaded file is too small ($FILE_SIZE bytes). This might be an error page."
    echo "File contents:"
    head -n 10 "$ZIP_FILE"
    echo "Please check if the release exists: $RELEASE_URL"
    rm -f "$ZIP_FILE"
    exit 1
fi

# Test if it's a valid ZIP file
if ! unzip -t "$ZIP_FILE" >/dev/null 2>&1; then
    echo "Error: Downloaded file is not a valid ZIP archive."
    echo "File size: $FILE_SIZE bytes"
    echo "File type: $(file "$ZIP_FILE" 2>/dev/null || echo 'unknown')"
    echo "First few lines of file:"
    head -n 5 "$ZIP_FILE"
    
    # Check if it's an HTML error page (common when URL is wrong)
    if head -n 1 "$ZIP_FILE" | grep -q "<html\|<!DOCTYPE"; then
        echo "The downloaded file appears to be an HTML page (likely 404 error)."
        echo "This suggests the release URL might be incorrect:"
        echo "  $RELEASE_URL"
        echo "Please check if version $VERSION exists on GitHub."
    fi
    
    rm -f "$ZIP_FILE"
    exit 1
fi

# Check if unzip is available
if ! command -v unzip >/dev/null 2>&1; then
    echo "Error: unzip not found. Please install unzip to extract the archive."
    exit 1
fi

# Extract the zip file
echo "Extracting BatchExport..."
echo "Archive contents:"
unzip -l "$ZIP_FILE"
echo ""

# Extract with verbose output for debugging
if ! unzip -o "$ZIP_FILE"; then
    echo "Error: Failed to extract $ZIP_FILE"
    echo "ZIP file info:"
    file "$ZIP_FILE" 2>/dev/null || echo "file command not available"
    ls -la "$ZIP_FILE"
    exit 1
fi

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
    echo "Error: $EXECUTABLE_NAME not found after extraction"
    echo "Contents of extracted files:"
    ls -la
    exit 1
fi

# Clean up zip file
rm -f "$ZIP_FILE"

# Clean up any remaining extracted directories if they're empty
find . -name "win-x64" -type d -empty -delete 2>/dev/null || true
find . -name "*x64*" -type d -empty -delete 2>/dev/null || true

echo "Extracted and cleaned up"

# Verify the executable
echo "Verifying BatchExport installation..."
if [ -f "$EXECUTABLE_NAME" ]; then
    FILE_SIZE=$(stat -f%z "$EXECUTABLE_NAME" 2>/dev/null || stat -c%s "$EXECUTABLE_NAME" 2>/dev/null || echo "unknown")
    echo "BatchExport executable found"
    echo "  Path: $BATCH_EXPORT_DIR/$EXECUTABLE_NAME"
    echo "  Size: $FILE_SIZE bytes"
    
    # Make executable (in case we're on WSL or similar)
    chmod +x "$EXECUTABLE_NAME" 2>/dev/null || true
    
    echo ""
    echo "BatchExport $VERSION installed successfully!"
    echo ""
    echo "Usage:"
    echo "  $BATCH_EXPORT_DIR/$EXECUTABLE_NAME [options]"
    echo ""
    echo "To use from Python:"
    echo "  executable_path = r'$BATCH_EXPORT_DIR\\$EXECUTABLE_NAME'"
    
else
    echo "Error: Installation verification failed"
    exit 1
fi

echo "================================================"
echo "Installation Complete"
echo "================================================"
