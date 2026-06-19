#!/usr/bin/env bash
# Build and run the Jetson perception container with GPU + caches mounted.
# Usage: ./run.sh            # interactive shell
#        ./run.sh <cmd...>   # run a command in the container
set -euo pipefail

cd "$(dirname "$0")/.."   # -> jetson-perception/

IMAGE="${AIMER_IMAGE:-aimer:dev}"
INSTALL_NANOOWL="${INSTALL_NANOOWL:-0}"
HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
PIP_CACHE_DIR_HOST="${PIP_CACHE_DIR_HOST:-$HOME/.cache/pip}"

mkdir -p models "$HF_HOME" "$PIP_CACHE_DIR_HOST"

DOCKER=(docker)
if ! docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
fi

"${DOCKER[@]}" build \
    --build-arg INSTALL_NANOOWL="$INSTALL_NANOOWL" \
    -t "$IMAGE" \
    -f docker/Dockerfile .

# Add a camera device (e.g. --device /dev/video0) once moving past static-image testing.
"${DOCKER[@]}" run --rm -it \
    --runtime nvidia \
    --network host \
    -e HF_HOME=/root/.cache/huggingface \
    -e HF_TOKEN="${HF_TOKEN:-}" \
    -v "$(pwd)/models:/models" \
    -v "$(pwd):/workspace/jetson-perception" \
    -v "$HF_HOME:/root/.cache/huggingface" \
    -v "$PIP_CACHE_DIR_HOST:/root/.cache/pip" \
    "$IMAGE" "$@"
