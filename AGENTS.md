# AGENTS.md — Project context for coding agents

This is the vendor-neutral context file for any coding agent (Claude, or others)
working on this repo. Read this first, then the subproject `AGENTS.md` for whichever
side you're touching. The durable "why" lives in [docs/context/](docs/context/).

> **Current status: SCAFFOLD ONLY — and deliberately minimal.** This document describes the
> full target system (the north star). In the repo *right now*, only the **NanoOWL bring-up** on
> the Jetson is scaffolded (see `jetson-perception/`). The STM32 firmware is a deferred placeholder
> (`stm32-gimbal/` holds docs only; it'll be generated in CubeMX later). Everything is stubs
> (`TODO`/`NotImplementedError`) — don't assume any function works. Build features in pipeline
> order, starting from NanoOWL.

## What this project is
A voice-driven open-vocabulary auto-aiming camera gimbal. See [README.md](README.md)
for the elevator pitch and [docs/architecture.md](docs/architecture.md) for the data flow.

```
voice query ─► STT ─► PaliGemma (VLM, sees frame+query) ─► target choice
camera (CSI) ─► NanoOWL (open-vocab detect, TensorRT) ─► boxes ──┘
                                  │
                       target box → pixel error (dx,dy) from frame center
                                  │  UART (binary frame + crc, bidirectional)
                                  ▼
              STM32N6 (FreeRTOS): 2× positional PID ─► 2× 50Hz PWM servos (pan/tilt)
                                  │  telemetry (angles, status) ──► back to Jetson
```

## Repo map
| Path | What | Stack |
|------|------|-------|
| `jetson-perception/` | Perception + control-target pipeline | Python 3, Docker (NVIDIA L4T), TensorRT |
| `stm32-gimbal/` | Gimbal firmware (UART, PID, PWM) | C, STM32CubeIDE + CubeMX HAL, FreeRTOS |
| `docs/` | Architecture, UART protocol, hardware, decisions | Markdown |

## Locked design decisions
| Area | Choice |
|------|--------|
| Open-vocab CV | NanoOWL + TensorRT |
| VLM | PaliGemma (sees image + query) |
| Control loop | Jetson sends **pixel error**; STM32 runs the PID |
| STM32 toolchain | STM32CubeIDE + CubeMX (HAL) |
| Camera | CSI (IMX219/IMX477) via GStreamer |
| Servos | Standard 50 Hz hobby positional servos |
| Query input | Voice → speech-to-text |
| UART | Binary packed frame + checksum, **bidirectional** |
| STM32 FW | FreeRTOS |
| Jetson env | Docker (jetson-containers / L4T base) |
| STM32 scope | Lean motor-controller only (no on-NPU CV) |
| Protocol source | Duplicated in each codebase; canonical human spec in `docs/uart-protocol.md` |
| License | MIT |

Full rationale: [docs/context/decisions.md](docs/context/decisions.md).

## The UART contract (must stay in sync on both sides)
Canonical spec: [docs/uart-protocol.md](docs/uart-protocol.md). It is **duplicated** in code
(`jetson-perception/.../comms/protocol.py` and `stm32-gimbal/App/Src/protocol.c`). If you change
the frame layout, change the doc and **both** implementations together.

## Where to start
- Perception side → [jetson-perception/AGENTS.md](jetson-perception/AGENTS.md)
- Firmware side → [stm32-gimbal/AGENTS.md](stm32-gimbal/AGENTS.md)

## House rules
- Keep the two `protocol` implementations byte-for-byte compatible with `docs/uart-protocol.md`.
- Keep hand-written STM32 code in `stm32-gimbal/App/` so CubeMX regeneration never clobbers it.
- No mock/simulated data — this is a hardware-in-the-loop project (user directive).
