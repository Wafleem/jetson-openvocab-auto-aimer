# AGENTS.md — stm32-gimbal

Gimbal control firmware for the STM32N6 Nucleo. C, STM32CubeIDE + CubeMX (HAL), FreeRTOS.
Read the root [../AGENTS.md](../AGENTS.md) first.

> **Status: deferred / placeholder.** Nothing is implemented here yet — the Jetson (NanoOWL)
> side is being built first. This folder intentionally holds only this file, the README, and
> `docs/pinout.md`. Do not scaffold firmware until that work starts.

## Planned role (when work begins)
Receive **pixel error (dx, dy)** from the Jetson over UART, run **two positional PID loops**
(pan + tilt), drive **two 50 Hz hobby servos**, and return telemetry. Lean motor-controller only.

## Planned setup
1. Generate the project in **STM32CubeMX** for the STM32N6 Nucleo: 2× TIM PWM @ 50 Hz, 1× USART
   (DMA), FreeRTOS. This creates `Core/`, `Drivers/`, the `.ioc`, and project files.
2. Put hand-written code in a new `App/` folder (outside generated dirs): `pid`, `servo`,
   `protocol` (mirror of [../docs/uart-protocol.md](../docs/uart-protocol.md)), `uart_comms`,
   `control_task`.

See [docs/pinout.md](docs/pinout.md) for the peripheral/pin plan.
