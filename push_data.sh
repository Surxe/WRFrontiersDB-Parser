#!/bin/bash
set -e

# === RUN PARSER ===
echo "Running parser..."
python3 src/parse.py

# Load GH_DATA_REPO_PAT from .env if it exists
if [ -f .env ]; then
        export GH_DATA_REPO_PAT=$(grep '^GH_DATA_REPO_PAT=' .env | cut -d '=' -f2- | sed 's/^"//;s/"$//')
fi

# === CONFIGURATION ===
DATA_REPO_URL="https://${GH_DATA_REPO_PAT}@github.com/Surxe/WRFrontiersDB-Data.git"
DATA_REPO_DIR="WRFrontiersDB-Data"
OUTPUT_DIR="output"    # this should match PARAMS.output_path

DEFAULT_NEW_GAME_VERSION=$(cat game_version.txt)
NEW_GAME_VERSION="${1:-$DEFAULT_NEW_GAME_VERSION}"
TARGET_BRANCH="${2:-testing-grounds}"

# If NEW_GAME_VERSION is not empty and different from DEFAULT_NEW_GAME_VERSION, update game_version.txt
if [ "$NEW_GAME_VERSION" != "$DEFAULT_NEW_GAME_VERSION" ]; then
    echo "$NEW_GAME_VERSION" > game_version.txt
    echo "Updated game_version.txt with: $NEW_GAME_VERSION"
fi

# Validate TARGET_BRANCH
if [ "$TARGET_BRANCH" != "testing-grounds" ] && [ "$TARGET_BRANCH" != "main" ]; then
    echo "❌ Invalid branch '$TARGET_BRANCH'. Only 'testing-grounds' and 'main' are allowed."
    exit 1
fi

echo "Using game version: $NEW_GAME_VERSION"
echo "Using branch: $TARGET_BRANCH"
echo "Using branch: $TARGET_BRANCH"

# Saves data to data repository and archives previous data

# === CLONE DATA REPO IF NOT PRESENT ===
# Set Git environment variables to avoid config issues on Windows
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export HOME="${USERPROFILE:-$HOME}"

if [ ! -d "$DATA_REPO_DIR" ]; then
    echo "Cloning WRFrontiersDB-Data..."
    git clone "$DATA_REPO_URL" "$DATA_REPO_DIR"
else
    echo "Repository already exists, deleting..."
    rm -rf "$DATA_REPO_DIR"
    echo "Re-cloning WRFrontiersDB-Data..."
    git clone "$DATA_REPO_URL" "$DATA_REPO_DIR"
fi

# Configure Git settings for the cloned repository
cd "$DATA_REPO_DIR"
git config --local user.email "parser@example.com"
git config --local user.name "Parser"
git config --local credential.helper ""

# Switch to target branch
echo "Switching to branch: $TARGET_BRANCH"
git checkout "$TARGET_BRANCH" || git checkout -b "$TARGET_BRANCH"

cd ..

# === GET LATEST COMMIT TITLE AND DATE ===
LATEST_COMMIT=$(git log -1 --format="%s - %ad" --date=short)
echo "Latest commit: $LATEST_COMMIT"
cd "$DATA_REPO_DIR"

# Determine the game version to archive (in current/version.txt)
CURRENT_PATH="current"
if [ -f "$CURRENT_PATH/version.txt" ]; then
    GAME_VERSION_TO_ARCHIVE=$(cat "$CURRENT_PATH/version.txt")
    echo "Will archive version $GAME_VERSION_TO_ARCHIVE from current/version.txt"
else
    echo "No current/version.txt found, will not archive any data."
fi

# Only archive if the game version to archive is different to the new version
if [ "$GAME_VERSION_TO_ARCHIVE" != "$NEW_GAME_VERSION" ]; then
    ARCHIVE_PATH="archive/$GAME_VERSION_TO_ARCHIVE"
    # Move all files from current/*.ext to archive/<version>/*.ext
    mkdir -p "$ARCHIVE_PATH"
    if [ -d "$CURRENT_PATH" ]; then
        echo "Archiving current data to $ARCHIVE_PATH..."
        mv "$CURRENT_PATH"/* "$ARCHIVE_PATH"/
    else
        echo "No current data to archive."
    fi
fi

# Delete all files from current/*
# This is to ensure that we start fresh for the new game version
if [ -d "$CURRENT_PATH" ]; then
    echo "Deleting old current data..."
    rm -rf "$CURRENT_PATH"/*
else
    echo "No current directory found, creating the dir..."
    mkdir -p "$CURRENT_PATH"
fi

echo "Copying new output to current/..."
# Copy all files from thisrepo/output/*.ext to thisrepo/WRFrontiersDB-Data/current/*.ext
# This will happen even if the game version is the same, overwriting the current files.
cp -r "../$OUTPUT_DIR"/* "$CURRENT_PATH/"
# Write version file
echo "$NEW_GAME_VERSION" > "$CURRENT_PATH/version.txt"

# === COMMIT AND PUSH ===
git add .
git commit -m "Data for version:$NEW_GAME_VERSION from latest Parser commit:$LATEST_COMMIT" || echo "Nothing to commit."
git push origin "$TARGET_BRANCH"

cd ..
echo "✅ Data updated successfully and pushed to branch '$TARGET_BRANCH'."
