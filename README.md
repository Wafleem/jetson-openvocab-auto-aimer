# jetson-openvocab-auto-aimer

A voice-driven, open-vocabulary auto-aiming camera gimbal.

Speak a target ("the red mug"). A **Jetson Orin Nano 8GB** runs NanoOWL
(open-vocab detection on TensorRT) plus a PaliGemma VLM that sees the
camera frame and the query, picks the target, and computes its pixel
offset from frame center. That offset is sent over **USB CDC** to an
**STM32N6 Nucleo** running FreeRTOS, which closes two positional PID
loops to drive a pan-tilt gimbal (two PWM servos) until the
target is centered. Telemetry returns over the same link.

On the Jetson, use `./run.sh live "a mug,a bottle" --vlm-query "the red mug"` to let PaliGemma
choose among NanoOWL candidates. See [`jetson-perception/README.md`](jetson-perception/README.md)
for model access, Docker setup, camera checks, and live operation.

## Layout
- `jetson-perception/` — Python perception + control-target pipeline (Docker).
- `stm32-gimbal/` — STM32CubeIDE/HAL firmware: USB CDC, FreeRTOS, PID, PWM servos.
- `docs/` — architecture, SP wire protocol, hardware notes, decisions.
