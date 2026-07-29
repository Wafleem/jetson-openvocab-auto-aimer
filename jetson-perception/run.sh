#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

IMAGE="aimer:nanoowl"
ENGINE="$(pwd)/models/owl_image_encoder_patch32.engine"
CACHE="${HOME}/.cache/huggingface"

if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
else
    DOCKER=(sudo docker)
fi

usage() {
    cat <<'EOF'
NanoOWL commands:
  ./run.sh setup
  ./run.sh engine
  ./run.sh detect PHOTO "a person,a red mug"
  ./run.sh shell

Run them in that order the first time.
EOF
}

container() {
    mkdir -p models "$CACHE"
    "${DOCKER[@]}" run --rm --device nvidia.com/gpu=all \
        -v "$(pwd)/models:/models" \
        -v "$CACHE:/root/.cache/huggingface" \
        "$@"
}

require_setup() {
    if ! "${DOCKER[@]}" image inspect "$IMAGE" >/dev/null 2>&1; then
        echo "Container image is missing. Run: ./run.sh setup" >&2
        exit 1
    fi
}

case "${1:-}" in
    setup)
        "${DOCKER[@]}" build -t "$IMAGE" .
        ;;
    engine)
        require_setup
        container "$IMAGE" python3 /app/aimer.py engine
        ;;
    detect)
        require_setup
        if [[ $# -ne 3 ]]; then
            usage
            exit 1
        fi
        if [[ ! -f "$2" ]]; then
            echo "Photo not found: $2" >&2
            exit 1
        fi
        if [[ ! -f "$ENGINE" ]]; then
            echo "TensorRT engine is missing. Run: ./run.sh engine" >&2
            exit 1
        fi
        PHOTO="$(realpath "$2")"
        container -v "$PHOTO:/input/image:ro" "$IMAGE" \
            python3 /app/aimer.py detect /input/image "$3"
        ;;
    shell)
        require_setup
        container -it "$IMAGE" bash
        ;;
    help|-h|--help|"")
        usage
        ;;
    *)
        echo "Unknown command: $1" >&2
        usage
        exit 1
        ;;
esac
