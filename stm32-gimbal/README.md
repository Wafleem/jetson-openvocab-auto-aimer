# stm32-gimbal

Pan-tilt gimbal control firmware for the STM32N6 Nucleo. STM32CubeIDE + CubeMX (HAL), FreeRTOS.

The checked-in [CubeMX configuration](jetson-openvocab-autoaim-stm32.ioc) targets CubeMX 6.15,
STM32CubeN6 1.2.0, and X-CUBE-FREERTOS 1.3.1. Context ownership is intentional:

- `FSBL/` contains boot and external-memory setup only.
- `AppS/` contains the generated secure FreeRTOS companion.
- `AppNS/` contains the runtime peripherals and integration: FreeRTOS, USBX CDC ACM, UCPD/USB-PD,
  TIM2 PWM, and the generated hooks into `App/`.
- `App/` contains the handwritten SP stream parser, latest-value FreeRTOS message queue, CDC reader,
  servo PID/control task, and PWM startup. CubeMX regeneration must not overwrite this directory.

TIM2 CH1 on PA15 and TIM2 CH2 on PC0 produce 50 Hz PWM with 1500 us neutral pulses. The CDC reader
accepts the same raw 29-byte `SP` frames used by `nyush-rm-control/scripts/sentry_bridge.py`.

The CubeMX CLI `generate code` path produced the checked-in multicontext sources. CubeMX 6.15's
full `project generate` path exhausted or stalled in its Java process on this Windows host, so the
generated source tree and IOC are checked in without claiming that the CLI produced IDE/CMake
project metadata. Application changes belong only in CubeMX user-code regions or `App/`.

See [docs/pinout.md](docs/pinout.md) for the planned peripherals/wiring and the root
[../AGENTS.md](../AGENTS.md) + [../docs/](../docs/) for the full system design and SP protocol contract.
