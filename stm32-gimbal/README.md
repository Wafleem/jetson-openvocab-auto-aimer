# stm32-gimbal

Pan-tilt gimbal control firmware for the STM32N6 Nucleo. STM32CubeIDE + CubeMX (HAL), FreeRTOS.

**Status: deferred / placeholder.** Work is starting on the Jetson (NanoOWL) side first. The
firmware project will be generated in **STM32CubeMX** when we get here — that produces `Core/`,
`Drivers/`, the `.ioc`, and the project files. Hand-written application code (PID, servo, UART
protocol, control task) will then live in an `App/` folder kept outside the generated dirs.

See [docs/pinout.md](docs/pinout.md) for the planned peripherals/wiring and the root
[../AGENTS.md](../AGENTS.md) + [../docs/](../docs/) for the full system design and the UART contract.
