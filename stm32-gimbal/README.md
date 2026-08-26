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

TIM2 CH1 on PA15 and TIM2 CH2 on PC0 produce 50 Hz PWM with 1500 us neutral pulses. This timer
configuration is electrically correct, but PA15 is routed to the Nucleo debug connector rather than
an ordinary expansion header. Regenerate the PWM pins before wiring servos; see
[docs/pinout.md](docs/pinout.md). The CDC reader accepts the same raw 29-byte `SP` frames used by
`nyush-rm-control/scripts/sentry_bridge.py`.

## CubeMX regeneration checklist

1. Keep the `SecureNSecure` contexts: boot in FSBL, secure handoff in AppS, and the runtime in AppNS.
2. Keep USB1 OTG HS, UCPD1, USB-PD, USBX CDC ACM, and FreeRTOS CMSIS-RTOS2 in AppNS. Keep the
   USB-PD time base on TIM1.
3. Replace the two TIM2 PWM outputs with AppNS `PG2 / TIM14_CH1` (Arduino D11) and
   `PA3 / TIM16_CH1` (Arduino D10). For a 400 MHz timer clock, use prescaler `399`, period `19999`,
   PWM mode 1, high polarity, and pulse `1500` on both timers.
4. Generate STM32CubeIDE project metadata and ensure `App/*.c` is compiled into AppNS with `App/`
   on the include path. Do not add `App/` to FSBL or AppS.
5. Check `AppNS/Src/usbpd_dpm_core.c` after generation. `USBPD_DPM_InitOS()` must create the CAD
   queue and task; some generated output omitted both. The checked-in version contains the ST
   reference fix.
6. Confirm the generated AppNS linker script, startup assembly, HAL drivers, FreeRTOS middleware,
   and USBX middleware are present before treating the project as buildable.

The CubeMX CLI `generate code` path produced the checked-in multicontext sources. CubeMX 6.15's
full `project generate` path exhausted or stalled in its Java process on this Windows host, so the
generated source tree and IOC are checked in without claiming that the CLI produced IDE/CMake
project metadata. Application changes belong only in CubeMX user-code regions or `App/`.

See [docs/pinout.md](docs/pinout.md) for the planned peripherals/wiring and the root
[../AGENTS.md](../AGENTS.md) + [../docs/](../docs/) for the full system design and SP protocol contract.

## Host validation

The stream parser and the complete two-axis controller are independent of HAL and FreeRTOS so their
safety behavior can be checked on a development machine. The checks cover fragmented and corrupt
SP frames, CRC, hold mode, timeout-equivalent hold, PID history reset, servo rate limits, mechanical
end stops, and integral anti-windup.

```bash
cmake -S . -B build/host
cmake --build build/host
ctest --test-dir build/host --output-on-failure
```

These deterministic tests validate the firmware core; they do not replace the board checks for USB
enumeration, physical PWM timing, servo direction, supply integrity, or tuned gains.
