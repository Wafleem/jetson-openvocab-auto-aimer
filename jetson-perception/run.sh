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
  ./run.sh camera "a person,a red mug"
  ./run.sh shell

Run them in that order the first time.
EOF
}

container() {
    mkdir -p models "$CACHE"
    "${DOCKER[@]}" run --rm --device nvidia.com/gpu=all --ipc host \
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

require_engine() {
    if [[ ! -s "$ENGINE" ]]; then
        echo "TensorRT engine is missing. Run: ./run.sh engine" >&2
        exit 1
    fi
}

detect_photo() {
    local photo="$1"
    local prompts="$2"
    container -v "$photo:/input/image:ro" "$IMAGE" \
        python3 /app/aimer.py detect /input/image "$prompts"
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
        require_engine
        PHOTO="$(realpath "$2")"
        detect_photo "$PHOTO" "$3"
        ;;
    camera)
        require_setup
        require_engine
        if [[ $# -ne 2 ]]; then
            usage
            exit 1
        fi
        PHOTO="$(pwd)/models/camera.jpg"
        gst-launch-1.0 -q -e \
            nvarguscamerasrc sensor-id=0 num-buffers=1 ! \
            'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! \
            nvvidconv ! 'video/x-raw,format=I420' ! jpegenc ! \
            filesink location="$PHOTO"
        if [[ ! -s "$PHOTO" ]]; then
            echo "The CSI camera did not produce a frame. Check the ribbon cable and reboot after enabling the camera overlay." >&2
            exit 1
        fi
        echo "Captured: $PHOTO"
        detect_photo "$PHOTO" "$2"
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
