# AGENTS.md — stm32-gimbal

Gimbal control firmware for the STM32N6 Nucleo. C, STM32CubeIDE + CubeMX (HAL), FreeRTOS.
Read the root [../AGENTS.md](../AGENTS.md) first.

> **Status: generated and integrated.** The CubeMX multicontext project, AppNS USB CDC reader,
> FreeRTOS data sharing, servo control task, and TIM2 PWM startup are checked in.

## Runtime role
Receive **yaw/pitch angular error offsets** from the Jetson over USB CDC, run **two positional PID loops**
(pan + tilt), drive **two 50 Hz hobby servos**, and return telemetry. Lean motor-controller only.

## Project layout
- Keep boot-only generated code in `FSBL/`.
- Keep runtime generated code and peripheral ownership in `AppNS/`.
- Keep hand-written code in `App/`; CubeMX regeneration must not clobber it.
- Keep the raw 29-byte SP layout compatible with [../docs/uart-protocol.md](../docs/uart-protocol.md)
  and the Jetson USB CDC bridge.

See [docs/pinout.md](docs/pinout.md) for the peripheral/pin plan.
