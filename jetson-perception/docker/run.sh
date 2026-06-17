#!/usr/bin/env bash
# Build and run the NanoOWL container with GPU + models mounted.
# Usage: ./run.sh            # interactive shell
#        ./run.sh <cmd...>   # run a command in the container
set -euo pipefail

cd "$(dirname "$0")/.."   # -> jetson-perception/

IMAGE=aimer:dev

docker build -t "$IMAGE" -f docker/Dockerfile .

# Add a camera device (e.g. --device /dev/video0) once moving past static-image testing.
docker run --rm -it \
    --runtime nvidia \
    --network host \
    -v "$(pwd)/models:/models" \
    -v "$(pwd):/workspace/jetson-perception" \
    "$IMAGE" "$@"
