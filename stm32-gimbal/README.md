# stm32-gimbal

Pan-tilt gimbal control firmware for the STM32N6 Nucleo. STM32CubeIDE + CubeMX (HAL), FreeRTOS.

The checked-in [CubeMX configuration](jetson-openvocab-autoaim-stm32.ioc) targets CubeMX 6.15,
STM32CubeN6 1.2.0, and X-CUBE-FREERTOS 1.3.1. Context ownership is intentional:

- `FSBL/` contains boot and external-memory setup only.
- `AppS/` contains the generated secure FreeRTOS companion.
- `AppNS/` contains the runtime peripherals and integration: FreeRTOS, USBX CDC ACM, UCPD/USB-PD,
  TIM14/TIM16 PWM, and the generated hooks into `App/`.
- `App/` contains the handwritten SP stream parser, latest-value FreeRTOS message queue, CDC reader,
  telemetry writer, servo PID/control task, and PWM startup. CubeMX regeneration must not overwrite
  this directory.

TIM14 CH1 on PG2 (Arduino D11) and TIM16 CH1 on PA3 (Arduino D10) produce 50 Hz PWM with 1500 us
neutral pulses. Both outputs are on ordinary Nucleo expansion-header pins; see
[docs/pinout.md](docs/pinout.md). The CDC reader accepts the same raw 29-byte `SP` frames used by
`nyush-rm-control/scripts/sentry_bridge.py`.

The LRUN flash layout follows ST's Nucleo TrustZone template. The signed secure image starts at
external-flash offset `0x00100000` and the signed non-secure image at `0x00180000`; each slot is
512 KiB. The FSBL copies them to AXI SRAM1 and AXI SRAM2 respectively before entering AppS. AppS
marks AXI SRAM2, the command-link peripherals, the two PWM timers, and their GPIO pins non-secure
before it jumps to AppNS.

## CubeMX regeneration checklist

1. Keep the `SecureNSecure` contexts: boot in FSBL, secure handoff in AppS, and the runtime in AppNS.
2. Keep USB1 OTG HS, UCPD1, USB-PD, USBX CDC ACM, and FreeRTOS CMSIS-RTOS2 in AppNS. Keep the
   USB-PD time base on TIM1.
3. Keep AppNS `PG2 / TIM14_CH1` (Arduino D11) and `PA3 / TIM16_CH1` (Arduino D10). For the 400 MHz
   timer clock, keep prescaler `399`, period `19999`, PWM mode 1, high polarity, and pulse `1500` on
   both timers.
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

See [docs/pinout.md](docs/pinout.md) for the peripherals/wiring and the root
[../AGENTS.md](../AGENTS.md) + [../docs/](../docs/) for the full system design and SP protocol contract.

## Host validation

The stream parser and the complete two-axis controller are independent of HAL and FreeRTOS so their
safety behavior can be checked on a development machine. The checks cover fragmented and corrupt
SP frames, CRC, hold mode, timeout-equivalent hold, PID history reset, servo rate limits, mechanical
end stops, integral anti-windup, and the exact STM32-to-Jetson telemetry layout.

```bash
cmake -S . -B build/host
cmake --build build/host
ctest --test-dir build/host --output-on-failure
```

These deterministic tests validate the firmware core; they do not replace the board checks for USB
enumeration, physical PWM timing, servo direction, supply integrity, or tuned gains.

## Arm target validation

The target check compiles every handwritten, AppNS, AppS, and FSBL C translation unit into a real
Cortex-M55 object with warnings treated as errors. It uses the exact Cube packages recorded by the
IOC: STM32CubeN6 1.2.0 and X-CUBE-FREERTOS 1.3.1.

```bash
./tools/fetch-validation-deps.sh
ARM_GCC=/path/to/arm-none-eabi-gcc ./tools/validate.sh
ARM_GCC=/path/to/arm-none-eabi-gcc ./tools/build-target.sh
```

Install Arm's GNU toolchain with its bundled Newlib headers; on macOS, the Homebrew
`gcc-arm-embedded` cask provides that distribution. `validate.sh` also runs the sanitizer-backed host
tests and checks that the IOC retains the expansion-header PWM routing and USB-PD initialization.
`build-target.sh` then links real FSBL, AppS, and AppNS ELFs and emits their raw binaries under
`build/target/`.
