#!/bin/bash
# Ensure we're in the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Export environment variables from tests/.env
if [ -f "tests/.env" ]; then
    echo "[INFO] Loading environment variables from tests/.env..."
    set -a  # Automatically export all variables
    source "tests/.env"
    set +a
    echo "[INFO] LITELLM_MASTER_KEY loaded (length: ${#LITELLM_MASTER_KEY})"
else
    echo "[ERROR] tests/.env not found"
    exit 1
fi

# Run the test suite
echo "[INFO] Running test suite..."
python3 tests/test_route.py "$@"
