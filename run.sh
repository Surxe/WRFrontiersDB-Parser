#!/bin/bash
set -e

# Main script to run the parser and push data to WRFrontiersDB-Data repo
# 
# Usage:
#   ./run.sh --EXPORTS_PATH <path> --GAME_VERSION <version> [--TARGET_BRANCH <branch>] [--LOG_LEVEL <level>]
#
# Parameters:
#   --EXPORTS_PATH  (required) Path to the directory containing game export data
#   --GAME_VERSION  (required) Game version identifier for the data being processed
#   --TARGET_BRANCH (optional) Git branch to push to (default: testing-grounds)
#   --LOG_LEVEL     (optional) Logging verbosity: DEBUG, INFO, or silent (default: DEBUG)
#
# Examples:
#   ./run.sh --EXPORTS_PATH "F:/WarRobotsFrontiersDB/2025-09-09" --GAME_VERSION "2025-09-09"
#   ./run.sh --EXPORTS_PATH "F:/WarRobotsFrontiersDB/2025-09-09" --GAME_VERSION "2025-09-09" --TARGET_BRANCH main --LOG_LEVEL INFO

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
            PARSE_ARGS+=("$1")
            shift
            ;;
    esac
done

# === VALIDATION ===
# Verify that GAME_VERSION is set
if [ -z "$NEW_GAME_VERSION" ]; then
    echo "❌ Error: --GAME_VERSION is required"
    exit 1
fi

# Set default LOG_LEVEL if not provided
if [ -z "$LOG_LEVEL" ]; then
    LOG_LEVEL="DEBUG"
fi

# === RUN PARSER ===
if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Running parser with args: ${PARSE_ARGS[@]}"
fi
python src/parse.py "${PARSE_ARGS[@]}"

# === PUSH DATA ===
# Call the push_data.sh script to handle git operations
PUSH_ARGS=()
if [ -n "$NEW_GAME_VERSION" ]; then
    PUSH_ARGS+=(--GAME_VERSION "$NEW_GAME_VERSION")
fi
if [ -n "$TARGET_BRANCH" ]; then
    PUSH_ARGS+=(--TARGET_BRANCH "$TARGET_BRANCH")
fi
if [ -n "$LOG_LEVEL" ]; then
    PUSH_ARGS+=(--LOG_LEVEL "$LOG_LEVEL")
fi

./push_data.sh "${PUSH_ARGS[@]}"