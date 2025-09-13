#!/bin/bash
set -e

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

# === RUN PARSER ===
if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Running parser with args: ${PARSE_ARGS[@]}"
fi
python3 src/parse.py "${PARSE_ARGS[@]}"

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