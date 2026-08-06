# SP Command Protocol (USB CDC)

This is the canonical Jetson-to-STM32 contract. It matches the 29-byte `SP` command used by the
NYU RoboMaster CV repository at commit `4c7a568`, but gives yaw and pitch one fixed meaning:
**current angular error from the camera center**, in radians.

> Status: implemented by `stm32-gimbal/App/gimbal_protocol.c`. The filename is retained for stable
> links from older project documentation.

## Transport settings

- USB CDC ACM carries the frame bytes unchanged. A host may select 115200 8N1, but USB CDC does not
  use that line rate electrically.
- Fixed-length frames; all multi-byte values are little-endian.
- Floats are 32-bit IEEE-754 values.

## Jetson to STM32: aim command

Total length: 29 bytes.

| Bytes | Type | Name | Meaning |
|-------|------|------|---------|
| 0-1 | `uint8[2]` | header | ASCII `SP` (`0x53 0x50`) |
| 2 | `uint8` | mode | `0` hold, `1` track, `2` track + fire request (reserved for later) |
| 3-6 | `float32` | yaw_error | Horizontal angular error in radians; target right is negative |
| 7-10 | `float32` | yaw_velocity | Reserved feed-forward; send `0.0` |
| 11-14 | `float32` | yaw_acceleration | Reserved feed-forward; send `0.0` |
| 15-18 | `float32` | pitch_error | Vertical angular error in radians; target below is positive |
| 19-22 | `float32` | pitch_velocity | Reserved feed-forward; send `0.0` |
| 23-26 | `float32` | pitch_acceleration | Reserved feed-forward; send `0.0` |
| 27-28 | `uint16` | crc | CRC over bytes 0-26 |

The 2D solver produces the errors from the target center and calibrated camera field of view:

```text
x = (target_x - image_width / 2) / (image_width / 2)
y = (target_y - image_height / 2) / (image_height / 2)
yaw_error   = -atan(x * tan(horizontal_fov / 2))
pitch_error =  atan(y * tan(vertical_fov / 2))
```

These are continuous controller errors, not one-time position increments. While `mode=1`, the
STM32 repeatedly uses them to compute a limited movement rate and update each positional servo
setpoint. It must not add the entire error to the servo angle on every received packet.

While `mode=0`, the STM32 ignores all six float fields, holds its current servo positions, and
clears or freezes PID integral state. This prevents target loss from commanding a return to zero.

## CRC-16

Use CRC-16/MCRF4XX:

- polynomial `0x1021`, reflected implementation `0x8408`
- initial value `0xFFFF`
- input and output reflected
- final XOR `0x0000`
- check value for ASCII `123456789`: `0x6F91`
- append the low CRC byte first

Equivalent update for each byte:

```text
crc = (crc >> 8) XOR table[(crc XOR byte) AND 0xFF]
```

## STM32 to Jetson

Telemetry remains required, but its frame is deferred until the STM32 project exists and its
available feedback is known. Hobby servos provide no measured shaft angle, so the first telemetry
will report commanded setpoints and status rather than claiming measured position.

## Timing and safety

- Send one command for every valid processed camera frame.
- Send `mode=0` immediately when tracking is not confirmed.
- The STM32 must enter hold mode when valid packets stop arriving for a configured timeout.
- Reject a frame with a bad header, wrong length, non-finite float, or bad CRC.
