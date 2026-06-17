# Hardware

> Fill in concrete part numbers, pins, and ports as the rig is assembled. Values marked TBD/example
> are placeholders.

## Compute
- **Jetson Orin Nano Developer Kit, 8 GB** — runs perception (NanoOWL + PaliGemma) under Docker.
- **STM32N6 Nucleo dev board** — runs gimbal firmware (FreeRTOS). Lean motor-controller role;
  the Neural-ART NPU is unused for now.

## Camera
- CSI MIPI camera (IMX219 or IMX477) on the Jetson CSI connector.
- Accessed via GStreamer `nvarguscamerasrc`. Resolution/fps set in `jetson-perception/config/default.yaml`.

## Gimbal / actuators
- 2-axis pan-tilt bracket.
- 2× standard hobby servos (50 Hz PWM, ~1.0–2.0 ms pulse → angle). e.g. MG996R / SG90 (TBD).
- Servos need their own power supply (do NOT power from the Nucleo). Common ground with the STM32.

## STM32 peripheral map (TBD — record once CubeMX is configured)
| Function | Peripheral | Pin(s) | Notes |
|----------|-----------|--------|-------|
| Pan servo PWM | TIMx CHx | TBD | 50 Hz, CCR = pulse width |
| Tilt servo PWM | TIMx CHy | TBD | 50 Hz |
| UART to Jetson | USARTx | TX/RX TBD | binary protocol, see uart-protocol.md |
| Control tick | TIMz / RTOS tick | — | fixed-rate PID |

## Wiring: Jetson ↔ STM32 UART
- Jetson TX → STM32 RX, Jetson RX → STM32 TX, **common GND**.
- **Level check:** Jetson GPIO/UART is 3.3 V; confirm the STM32 UART pins are 3.3 V tolerant (they are
  on STM32) — do not connect 5 V logic directly.
- Jetson side device: `/dev/ttyTHS*` (set via `SERIAL_PORT`).

## Power notes
- Servos: separate 5–6 V supply sized for stall current.
- Keep servo power transients off the logic supplies.
