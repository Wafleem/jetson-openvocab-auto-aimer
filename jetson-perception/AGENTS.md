# AGENTS.md — jetson-perception

Jetson Orin Nano 8GB perception. Python, runs in a Docker container on JetPack.
Read the root [../AGENTS.md](../AGENTS.md) first for the full system design.

> **Current milestone: NanoOWL bring-up.** This subproject is deliberately minimal right now —
> just enough to build a NanoOWL TensorRT engine and run open-vocab detection on an image.
> The full pipeline (PaliGemma VLM, speech-to-text, target-tracker → pixel error, UART to STM32)
> is documented in the root docs but **not yet scaffolded here**. Add those modules only as you
> reach them.

> **Scaffold:** `detector.py` has the right structure but its internals are `TODO` /
> `NotImplementedError`. Heavy deps (torch, nanoowl, tensorrt) only exist inside the container.

## What exists now (`src/aimer/`)
| File | Responsibility |
|------|----------------|
| `detector.py` | `NanoOwlDetector` — load the TRT engine, run open-vocab detection → `Detection` list. |
| `run_detect.py` | CLI: load engine, detect prompts in one image, print boxes. The smoke test. |

Plus: `scripts/build_engine.py` (build the engine), `docker/` (L4T + NanoOWL), `models/` (engines).

## First goal (definition of done for this milestone)
1. `docker/run.sh` builds an image with NanoOWL + torch2trt installed.
2. `scripts/build_engine.py` produces an image-encoder `.engine` in `/models`.
3. `python -m aimer.run_detect --engine ... --image ... --prompts "..."` prints detections.

## Next (deferred — don't build until NanoOWL works)
Camera (CSI/GStreamer) → live detection → PaliGemma target selection → pixel error → UART.
See [../docs/architecture.md](../docs/architecture.md).

## Conventions
- Keep heavy imports lazy (inside functions) so modules import on a dev machine without the Jetson stack.
- No mock data (hardware-in-the-loop project).
