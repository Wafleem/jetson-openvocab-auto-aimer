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
                         │                              target_tracker: box → pixel error (dx,dy)  │
                         │                              relative to frame center (+ smoothing)      │
                         │                                                    │                    │
                         └────────────────────────────────────────── UART TX │ ───────────────────┘
                                                                              ▼
                         ┌──────────────────────────── STM32N6 NUCLEO (FreeRTOS) ───────────────────┐
                         │  uart_comms: parse binary frame (sync+len+id+dx+dy+flags+crc)             │
                         │        │                                                                  │
                         │        ▼                                                                  │
                         │  control_task @ fixed rate:  PID_pan(dx) , PID_tilt(dy)                   │
                         │        │                                                                  │
                         │        ▼                                                                  │
                         │  servo: angle → PWM CCR (50 Hz)  ──► pan servo , tilt servo              │
                         │        │                                                                  │
                         │        └──► telemetry frame (pan_angle, tilt_angle, status) ──► UART TX ──┼─► back to Jetson
                         └───────────────────────────────────────────────────────────────────────┘
```

## Responsibilities
- **Jetson** owns all perception and decides *what* to aim at and *how far off* it is (in pixels).
  It does NOT command angles — it sends the error signal.
- **STM32** owns the *control*: it converts pixel error into servo motion via two independent
  positional PID loops, respects mechanical limits, and reports telemetry.

## Why pixel error (not angles)
Keeps the control loop and its tuning entirely on the deterministic real-time MCU; the Jetson stays
a pure perception node. The pixel→motion gain is absorbed into the PID gains on the STM32.

## Failure handling (to design later)
- Target lost → Jetson sets a flag in the frame; STM32 should hold position (decide: hold vs. recenter).
- UART link timeout → STM32 should fail safe (stop commanding motion).

See [uart-protocol.md](uart-protocol.md) for the wire format and [context/](context/) for rationale.
