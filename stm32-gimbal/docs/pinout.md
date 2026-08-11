# STM32N6 Nucleo — pinout and peripherals

Source of truth: [../jetson-openvocab-autoaim-stm32.ioc](../jetson-openvocab-autoaim-stm32.ioc).

## Enabled peripherals

- **TIM2 CH1 + CH2 at 50 Hz** — pan and tilt servo PWM.
- **USB1 OTG HS + UCPD1 + USBX CDC ACM** — Jetson command link using the raw SP protocol.
- **FreeRTOS (CMSIS-RTOS2)** — USB receive and control tasks with a latest-value command queue.

## Pin map

| Signal | Peripheral / Channel | Pin | Notes |
|--------|----------------------|-----|-------|
| Pan servo PWM | TIM2_CH1 | PA15 | Current generated pin; JTDI/debug connector, do not use for normal servo wiring |
| Tilt servo PWM | TIM2_CH2 | PC0 | 50 Hz; 1000–2000 us pulse, 1500 us neutral |
| Jetson data | USB1 OTG HS CDC ACM | Nucleo USB-C | Data-capable USB cable |
| Servo ground | — | GND | Common with the external servo supply |

For the next regeneration, move pan to `PG2 / TIM14_CH1` (Arduino D11) and tilt to
`PA3 / TIM16_CH1` (Arduino D10). These are accessible expansion-header pins and leave TIM1 available
for the native USB-PD time base. The handwritten control task will need to use `htim14` channel 1
and `htim16` channel 1 after that regeneration.

## Timer math

- Current TIM2 input clock: 400 MHz.
- Prescaler: 399, producing a 1 MHz counter and a 1 us timer tick.
- Auto-reload: 19999, producing a 20 ms period (50 Hz).
- CCR value therefore equals the commanded servo pulse width in microseconds.

## Wiring reminders (see ../../docs/context/hardware.md)

- Servos powered from a **separate 5–6 V supply** (not the Nucleo), common ground.
- Connect the Jetson to the Nucleo USB-C device port with a data-capable cable.
