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
  ./run.sh camera-check
  ./run.sh camera "a person,a red mug"
  ./run.sh shell

Run them in that order the first time.
EOF
}

camera_check() {
    if compgen -G '/dev/video*' >/dev/null; then
        echo "CSI camera found:"
        ls -1 /dev/video*
        return 0
    fi

    echo "No CSI video device was found."
    local kernel_log
    kernel_log="$(dmesg 2>/dev/null || sudo dmesg 2>/dev/null || true)"
    if grep -qE 'imx219 .*error during i2c read probe \(-121\)' <<<"$kernel_log"; then
        cat <<'EOF'
CAM1 is configured for an IMX219, but the sensor did not answer over I2C.
Shut the Jetson down completely, disconnect power, and reseat both ribbon ends.
On the Jetson's 22-pin connector, the ribbon's gold contacts must face the board.
Then reconnect power, boot, and run: ./run.sh camera-check
EOF
    else
        echo "Check that the IMX219 CAM1 overlay is enabled, then reboot."
    fi
    return 1
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
    camera-check)
        camera_check
        ;;
    camera)
        if [[ $# -ne 2 ]]; then
            usage
            exit 1
        fi
        camera_check
        require_setup
        require_engine
        PHOTO="$(pwd)/models/camera.jpg"
        FRAME_PATTERN="/tmp/aimer-camera-frame-%03d.jpg"
        env -u DISPLAY -u WAYLAND_DISPLAY \
            __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/10_nvidia.json \
            gst-launch-1.0 -q -e \
            nvarguscamerasrc sensor-id=0 wbmode=3 num-buffers=45 ! \
            'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! \
            nvvidconv ! 'video/x-raw,format=I420' ! jpegenc ! \
            multifilesink location="$FRAME_PATTERN"
        cp /tmp/aimer-camera-frame-044.jpg "$PHOTO"
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
