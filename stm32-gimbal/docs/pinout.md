# STM32N6 Nucleo — pinout and peripherals

Source of truth: [../jetson-openvocab-autoaim-stm32.ioc](../jetson-openvocab-autoaim-stm32.ioc).
Board connector mapping: [ST UM3417](https://www.st.com/resource/en/user_manual/um3417-stm32n6-nucleo144-board-mb1940-stmicroelectronics.pdf).

## Enabled peripherals

- **TIM14 CH1 + TIM16 CH1 at 50 Hz** — pan and tilt servo PWM.
- **USB1 OTG HS + UCPD1 + USBX CDC ACM** — Jetson command link using the raw SP protocol.
- **FreeRTOS (CMSIS-RTOS2)** — USB receive and control tasks with a latest-value command queue.

## Pin map

| Signal | Peripheral / Channel | Pin | Notes |
|--------|----------------------|-----|-------|
| Pan servo PWM | TIM14_CH1 | PG2 / Arduino D11 | 50 Hz; 1000–2000 us pulse, 1500 us neutral |
| Tilt servo PWM | TIM16_CH1 | PA3 / Arduino D10 | 50 Hz; 1000–2000 us pulse, 1500 us neutral |
| Jetson data | USB1 OTG HS CDC ACM | Nucleo USB-C | Data-capable USB cable |
| Servo ground | — | GND | Common with the external servo supply |

These accessible expansion-header pins leave TIM1 available for the native USB-PD time base. The
handwritten control task drives `htim14` channel 1 and `htim16` channel 1.

## Timer math

- TIM14/TIM16 input clock: 400 MHz.
- Prescaler: 399, producing a 1 MHz counter and a 1 us timer tick.
- Auto-reload: 19999, producing a 20 ms period (50 Hz).
- CCR value therefore equals the commanded servo pulse width in microseconds.

## Wiring reminders (see ../../docs/context/hardware.md)

- Servos powered from a **separate 5–6 V supply** (not the Nucleo), common ground.
- Connect the Jetson to the Nucleo USB-C device port with a data-capable cable.
