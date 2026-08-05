# Architecture

End-to-end: a spoken query selects a target; the gimbal keeps it centered.

## Data flow
```
                         ┌──────────────────────── JETSON ORIN NANO 8GB ────────────────────────┐
                         │                                                                        │
  mic ──► STT (voice→text) ──► query string ──┐                                                   │
                         │                     ▼                                                   │
  CSI camera ──► frames ──► NanoOWL (open-vocab detect, TensorRT) ──► candidate boxes+labels       │
                         │                     │                              │                    │
                         │                     ▼                              ▼                    │
                         │            PaliGemma VLM (frame + query) ──► chosen target box          │
                         │                                                    │                    │
                         │                         2D solver: box → yaw/pitch angular error         │
                         │                         from calibrated FOV (+ smoothing)                │
                         │                                                    │                    │
                         └────────────────────────────────────────── UART TX │ ───────────────────┘
                                                                              ▼
                         ┌──────────────────────────── STM32N6 NUCLEO (FreeRTOS) ───────────────────┐
                         │  uart_comms: parse 29-byte SP frame (mode+angles+CRC-16)                  │
                         │        │                                                                  │
                         │        ▼                                                                  │
                         │  control_task: PID_pan(yaw_error), PID_tilt(pitch_error)                  │
                         │        │                                                                  │
                         │        ▼                                                                  │
                         │  servo: angle → PWM CCR (50 Hz)  ──► pan servo , tilt servo              │
                         │        │                                                                  │
                         │        └──► telemetry frame (pan_angle, tilt_angle, status) ──► UART TX ──┼─► back to Jetson
                         └───────────────────────────────────────────────────────────────────────┘
```

## Responsibilities
- **Jetson** owns perception and converts the target's image position into yaw/pitch angular error.
  These are offsets from camera center, not absolute servo positions.
- **STM32** owns the *control*: it converts angular error into servo motion via two independent
  positional PID loops, respects mechanical limits, and reports telemetry.

## Why angular error
The calibrated 2D FOV solver removes image-resolution and lens-FOV differences before the command
reaches the STM32. The real-time controller, limits, and PWM generation still remain on the MCU.

## Failure handling (to design later)
- Target lost → Jetson sends `mode=0`; STM32 holds position and clears/freezes PID integral state.
- UART link timeout → STM32 should fail safe (stop commanding motion).

See [uart-protocol.md](uart-protocol.md) for the wire format and [context/](context/) for rationale.
