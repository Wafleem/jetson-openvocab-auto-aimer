# Decisions (ADR-style log)

Captured during project kickoff. These are the choices the structure is built around. If you revisit
one, note it here with the date and reason.

| # | Decision | Choice | Why |
|---|----------|--------|-----|
| 1 | Open-vocab detector | **NanoOWL + TensorRT** | NVIDIA-optimized OWL-ViT for Jetson; best real-time perf on Orin Nano 8GB. |
| 2 | Language/vision model | **PaliGemma (VLM)** | Sees the camera frame + the query to select/refine the target, not just parse text. |
| 3 | Control split | **Jetson sends yaw/pitch angular error; STM32 runs PID** | Lens geometry stays with perception; deterministic motion control stays on the MCU. Supersedes the original pixel-error choice on 2026-07-29. |
| 4 | STM32 toolchain | **STM32CubeIDE + CubeMX (HAL)** | Official, standard for Nucleo; `.ioc`-driven init. |
| 5 | Camera | **CSI (IMX219/IMX477)** | Native Jetson MIPI path via GStreamer/nvarguscamerasrc. |
| 6 | Servos | **Standard 50 Hz hobby positional servos** | Internal position loop; STM32 PID adjusts the commanded angle. |
| 7 | Query input | **Voice → speech-to-text** | Spoken natural-language target. STT model TBD (e.g. faster-whisper / whisper.cpp). |
| 8 | Jetson link | **USB CDC carrying the RoboMaster-compatible 29-byte `SP` command with CRC-16** | Reuses the team's proven frame and Jetson bridge without consuming a hardware UART. Updated 2026-08-06. |
| 9 | STM32 firmware model | **FreeRTOS** | Separate USB receive and control tasks share a latest-value command queue. |
| 10 | Jetson environment | **Docker (jetson-containers / L4T base)** | Reproducible; isolates CUDA/TensorRT deps. |
| 11 | STM32 scope | **Lean motor-controller only** | No on-NPU (Neural-ART) CV for now; can revisit. |
| 12 | Folder names | `jetson-perception/`, `stm32-gimbal/` | Descriptive of each board's role. |
| 13 | Protocol source of truth | **Duplicated in each codebase**; canonical human spec in `docs/uart-protocol.md` | User chose duplication; doc keeps the two copies aligned. |
| 14 | Agent context | **AGENTS.md** (cross-provider) + `CLAUDE.md` pointer + `docs/context/` | Portable to any coding agent. |
| 15 | License | **MIT** | Permissive, simple. |
| 16 | Mock/sim data | **None — hardware-in-the-loop only** | User directive: no mock data. |

## Open questions (not yet decided)
- STT model + how voice capture is wired (mic device, push-to-talk vs. always-on).
- STM32-to-Jetson telemetry layout.
- Control loop rate on the STM32.
- Coordinate sign conventions / which physical servo is pan vs. tilt.
