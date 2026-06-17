# UART Protocol (canonical spec)

This document is the **single source of truth** for the Jetson ↔ STM32 link. The protocol is
implemented **twice** (Python on the Jetson, C on the STM32) — both implementations MUST match this
doc byte-for-byte. If you change anything here, update both:
- `jetson-perception/src/aimer/comms/protocol.py`
- `stm32-gimbal/App/Src/protocol.c` (+ `App/Inc/protocol.h`)

> Status: **DRAFT / stub.** Field sizes below are the intended starting point; confirm before
> implementing. Nothing is wired up yet.

## Physical layer (proposed)
- UART, 8N1, no flow control.
- Baud: **921600** (tune later; keep latency low). Defined in `app_config.h` and `.env`.
- Jetson port: a `/dev/ttyTHS*` (Orin UART) — set via `SERIAL_PORT` env var.

## Framing
All multi-byte integers are **little-endian**. Frames are fixed-length per message id.

```
byte 0 : SYNC   = 0xAA          (start-of-frame marker)
byte 1 : LEN    = payload length in bytes (excludes sync/len/crc)
byte 2 : MSG_ID
byte 3.. : PAYLOAD (LEN bytes)
last   : CRC8   over [MSG_ID + PAYLOAD]   (polynomial TBD, e.g. CRC-8/Maxim)
```

## Message: Jetson → STM32  `MSG_AIM` (id = 0x01)
Tells the gimbal how far the target is from frame center, in pixels.

| Field  | Type   | Notes |
|--------|--------|-------|
| dx     | int16  | horizontal error (target_x − center_x), +right |
| dy     | int16  | vertical error (target_y − center_y), +down |
| flags  | uint8  | bit0 = target_valid (0 = no target this frame) |

Payload = 5 bytes. Total frame = 1+1+1+5+1 = 9 bytes.

## Message: STM32 → Jetson  `MSG_TLM` (id = 0x81)
Telemetry / heartbeat back to the Jetson.

| Field      | Type   | Notes |
|------------|--------|-------|
| pan_angle  | int16  | current commanded pan angle, centi-degrees |
| tilt_angle | int16  | current commanded tilt angle, centi-degrees |
| status     | uint8  | bit0 = link_ok, bit1 = at_limit_pan, bit2 = at_limit_tilt |

Payload = 5 bytes. Total frame = 9 bytes.

## Timing / safety (to design)
- Jetson sends `MSG_AIM` every frame (~target rate TBD).
- STM32 treats absence of `MSG_AIM` for N ms as link loss → fail safe (stop motion).
- STM32 emits `MSG_TLM` at a fixed heartbeat rate.
