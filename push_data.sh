#!/bin/bash
set -e

# This script handles git operations to push parsed data from output/ directory
# to the WRFrontiersDB-Data repository, with automatic archiving of previous versions.
#
# Usage:
#   ./push_data.sh --GAME_VERSION <version> [--TARGET_BRANCH <branch>] [--LOG_LEVEL <level>]
#
# Parameters:
#   --GAME_VERSION   (required) Game version identifier for the data being pushed
#   --TARGET_BRANCH  (optional) Git branch to push to (default: testing-grounds)  
#   --LOG_LEVEL      (optional) Logging verbosity: DEBUG, INFO, or silent (default: DEBUG)
#
# Examples:
#   ./push_data.sh --GAME_VERSION "2025-09-09"
#   ./push_data.sh --GAME_VERSION "2025-09-09" --TARGET_BRANCH main --LOG_LEVEL INFO
#
# Requirements:
#   - GH_DATA_REPO_PAT environment variable or .env file with GitHub token
#   - output/ directory with parsed data files
#   - Git installed and configured

# Parse named arguments, assumes --arg1 val1 --arg2 val2 format, not --arg1=val1
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --GAME_VERSION)
            NEW_GAME_VERSION="$2"
            shift 2
            ;;
        --TARGET_BRANCH)
            TARGET_BRANCH="$2"
            shift 2
            ;;
        --LOG_LEVEL)
            LOG_LEVEL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Load GH_DATA_REPO_PAT from .env if it exists
# Only print if LOG_LEVEL is DEBUG
if [ -f .env ]; then
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Loading GH_DATA_REPO_PAT from .env"
    fi
    export GH_DATA_REPO_PAT=$(grep '^GH_DATA_REPO_PAT=' .env | cut -d '=' -f2- | sed 's/^"//;s/"$//')
fi

# === CONFIGURATION ===
DATA_REPO_URL="https://${GH_DATA_REPO_PAT}@github.com/Surxe/WRFrontiersDB-Data.git"
DATA_REPO_DIR="WRFrontiersDB-Data"
OUTPUT_DIR="output"    # this should match PARAMS.output_path

if [ -z "$TARGET_BRANCH" ]; then
    TARGET_BRANCH="testing-grounds"
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Using default branch: $TARGET_BRANCH"
    fi
fi

# Validate TARGET_BRANCH
# Only print if LOG_LEVEL is DEBUG
if [ "$TARGET_BRANCH" != "testing-grounds" ] && [ "$TARGET_BRANCH" != "main" ]; then
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "❌ Invalid branch '$TARGET_BRANCH'. Only 'testing-grounds' and 'main' are allowed."
    fi
    exit 1
fi

if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Using game version: $NEW_GAME_VERSION"
    echo "Using branch: $TARGET_BRANCH"
fi

# Saves data to data repository and archives previous data

# === CLONE DATA REPO IF NOT PRESENT ===
# Set Git environment variables to avoid config issues on Windows
export GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL=/dev/null
export HOME="${USERPROFILE:-$HOME}"

# Clone data repo. Lazily delete and re-clone to ensure a clean state.
# Only print git output if LOG_LEVEL is DEBUG or INFO
if [ ! -d "$DATA_REPO_DIR" ]; then
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Cloning WRFrontiersDB-Data..."
    fi
    if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
        git clone "$DATA_REPO_URL" "$DATA_REPO_DIR"
    else
        git clone "$DATA_REPO_URL" "$DATA_REPO_DIR" > /dev/null 2>&1
    fi
else
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Repository already exists, deleting..."
    fi
    rm -rf "$DATA_REPO_DIR"
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Re-cloning WRFrontiersDB-Data..."
    fi
    if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
        git clone "$DATA_REPO_URL" "$DATA_REPO_DIR"
    else
        git clone "$DATA_REPO_URL" "$DATA_REPO_DIR" > /dev/null 2>&1
    fi
fi

# Configure Git settings for the cloned repository
cd "$DATA_REPO_DIR"
if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
    git config --local user.email "parser@example.com"
    git config --local user.name "Parser"
    git config --local credential.helper ""
else
    git config --local user.email "parser@example.com" > /dev/null 2>&1
    git config --local user.name "Parser" > /dev/null 2>&1
    git config --local credential.helper "" > /dev/null 2>&1
fi

# Switch to target branch
if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Switching to branch: $TARGET_BRANCH"
fi
if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
    git checkout "$TARGET_BRANCH" || git checkout -b "$TARGET_BRANCH"
else
    git checkout "$TARGET_BRANCH" > /dev/null 2>&1 || git checkout -b "$TARGET_BRANCH" > /dev/null 2>&1
fi

# === GET LATEST COMMIT TITLE AND DATE (of parser repo) ===
# Only print git log output if LOG_LEVEL is DEBUG or INFO
cd .. # switch back to parser repo
if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
    LATEST_COMMIT=$(git log -1 --format="%s - %ad" --date=short)
    echo "Latest commit: $LATEST_COMMIT"
else
    LATEST_COMMIT=$(git log -1 --format="%s - %ad" --date=short 2>/dev/null)
fi

# Determine the game version to archive (in current/version.txt)
cd "$DATA_REPO_DIR" # switch to data repo
CURRENT_PATH="current"
if [ -f "$CURRENT_PATH/version.txt" ]; then
    GAME_VERSION_TO_ARCHIVE=$(cat "$CURRENT_PATH/version.txt")
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Will archive version $GAME_VERSION_TO_ARCHIVE from current/version.txt"
    fi
else
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "No current/version.txt found, will not archive any data."
    fi
fi

# === ARCHIVE OLD DATA (First Commit) ===
# Only archive if the game version to archive is different to the new version
if [ "$GAME_VERSION_TO_ARCHIVE" != "$NEW_GAME_VERSION" ]; then
    ARCHIVE_PATH="archive/$GAME_VERSION_TO_ARCHIVE"
    # Move all files from current/*.ext to archive/<version>/*.ext
    mkdir -p "$ARCHIVE_PATH"
    if [ -d "$CURRENT_PATH" ]; then
        if [ "$LOG_LEVEL" = "DEBUG" ]; then
            echo "Archiving current data to $ARCHIVE_PATH..."
        fi
        # Move all files and directories, handling non-empty dirs
        cp -a "$CURRENT_PATH"/. "$ARCHIVE_PATH"/
        rm -rf "$CURRENT_PATH"/*
        
        # Commit the archival changes
        if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
            git add .
            git commit -m "Archive version:$GAME_VERSION_TO_ARCHIVE data"
        else
            git add . > /dev/null 2>&1
            git commit -m "Archive version:$GAME_VERSION_TO_ARCHIVE data" > /dev/null 2>&1
        fi
        
        if [ "$LOG_LEVEL" = "DEBUG" ]; then
            echo "✅ Archived version $GAME_VERSION_TO_ARCHIVE and committed changes."
        fi
    else
        if [ "$LOG_LEVEL" = "DEBUG" ]; then
            echo "No current data to archive."
        fi
    fi
fi

# === UPDATE CURRENT DATA (Second Commit) ===
# Delete all files from current/* (if not already done during archival)
# This is to ensure that we start fresh for the new game version
if [ -d "$CURRENT_PATH" ]; then
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "Deleting old current data..."
    fi
    rm -rf "$CURRENT_PATH"/*
else
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "No current directory found, creating the dir..."
    fi
    mkdir -p "$CURRENT_PATH"
fi

if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Copying new output to current/..."
fi
# Copy all files from thisrepo/output/*.ext to thisrepo/WRFrontiersDB-Data/current/*.ext
# This will happen even if the game version is the same, overwriting the current files.
cp -r "../$OUTPUT_DIR"/* "$CURRENT_PATH/"
# Write version file
echo "$NEW_GAME_VERSION" > "$CURRENT_PATH/version.txt"

# Commit the new current data
if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
    git add .
    git commit -m "Update current data to version:$NEW_GAME_VERSION from latest Parser commit:$LATEST_COMMIT"
else
    git add . > /dev/null 2>&1
    git commit -m "Update current data to version:$NEW_GAME_VERSION from latest Parser commit:$LATEST_COMMIT" > /dev/null 2>&1
fi

if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "✅ Updated current data to version $NEW_GAME_VERSION and committed changes."
fi

# === PUSH ALL COMMITS ===
# Only print git push output if LOG_LEVEL is DEBUG or INFO
if [ "$LOG_LEVEL" = "DEBUG" ] || [ "$LOG_LEVEL" = "INFO" ]; then
    git push origin "$TARGET_BRANCH"
else
    git push origin "$TARGET_BRANCH" > /dev/null 2>&1
fi

cd ..
if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "✅ All changes committed and pushed successfully to branch '$TARGET_BRANCH'."
fi