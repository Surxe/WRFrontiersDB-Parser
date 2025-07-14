#!/bin/bash
set -e

# Load GH_DATA_REPO_PAT from .env if it exists
if [ -f .env ]; then
    export GH_DATA_REPO_PAT=$(grep '^GH_DATA_REPO_PAT=' .env | cut -d '=' -f2- | sed 's/^"//;s/"$//')
fi

# === CONFIGURATION ===
DATA_REPO_URL="https://${GH_DATA_REPO_PAT}@github.com/Surxe/WRFrontiersDB-Data.git"
DATA_REPO_DIR="WRFrontiersDB-Data"
OUTPUT_DIR="output"  # this should match PARAMS.output_path

# Prompt for game version
DEFAULT_GAME_VERSION=$(cat game_version.txt)
echo -n "Enter game version (yyyy-mm-dd) [default: $DEFAULT_GAME_VERSION]: "
read GAME_VERSION
if [ -z "$GAME_VERSION" ]; then
    GAME_VERSION=$DEFAULT_GAME_VERSION
else
    # Write the new version to game_version.txt
    echo "$GAME_VERSION" > game_version.txt
    echo "Updated game_version.txt with: $GAME_VERSION"
fi
echo "Using game version: $GAME_VERSION"

# === RUN PARSER ===
echo "Running parser..."
python3 src/parse.py

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
cd ..

# === GET LATEST COMMIT TITLE AND DATE ===
LATEST_COMMIT=$(git log -1 --format="%s - %ad" --date=short)
echo "Latest commit: $LATEST_COMMIT"
cd "$DATA_REPO_DIR"

# === ARCHIVE CURRENT ===
ARCHIVE_PATH="archive/$GAME_VERSION"
CURRENT_PATH="current"

echo "Archiving previous current data..."
mkdir -p "$ARCHIVE_PATH"
if [ -d "$CURRENT_PATH" ]; then
  # Find the existing version directory in current (should be only one)
  EXISTING_VERSION=$(ls -1 "$CURRENT_PATH" 2>/dev/null | head -n 1)
  if [ -n "$EXISTING_VERSION" ] && [ -d "$CURRENT_PATH/$EXISTING_VERSION" ]; then
    echo "Found existing version: $EXISTING_VERSION"
    # Only archive if it's a different version than the current game version
    if [ "$EXISTING_VERSION" != "$GAME_VERSION" ]; then
      echo "Archiving $EXISTING_VERSION (different from new version $GAME_VERSION)"
      # Archive to the existing version's archive directory
      EXISTING_ARCHIVE_PATH="archive/$EXISTING_VERSION"
      mkdir -p "$EXISTING_ARCHIVE_PATH"
      cp -r "$CURRENT_PATH/$EXISTING_VERSION"/* "$EXISTING_ARCHIVE_PATH"/ || true
    else
      echo "Existing version $EXISTING_VERSION matches new version $GAME_VERSION, skipping archive"
    fi
  fi
  rm -rf "$CURRENT_PATH"
fi

# === COPY NEW OUTPUT ===
echo "Copying new output to current/$GAME_VERSION..."
mkdir -p "$CURRENT_PATH/$GAME_VERSION"
cp -r "../$OUTPUT_DIR"/* "$CURRENT_PATH/$GAME_VERSION/"

# === COMMIT AND PUSH ===
git add .
git commit -m "Data for version:$GAME_VERSION from latest Parser commit:$LATEST_COMMIT" || echo "Nothing to commit."
git push

cd ..
echo "✅ Data updated successfully."
