# STM32N6 Nucleo — pinout & peripheral plan

> TBD until configured in STM32CubeMX. Fill these in from the `.ioc`, then keep this doc in sync.
> The CubeMX `.ioc` is generated/maintained locally and committed once it exists — it is intentionally
> NOT stubbed in this scaffold.

## Peripherals to enable in CubeMX
- **2× TIM PWM channels @ 50 Hz** — pan + tilt servos.
- **1× USART (with DMA)** — link to Jetson (binary protocol, see ../../docs/uart-protocol.md).
- **FreeRTOS (CMSIS-RTOS2)** — tasks: uart_rx, control, telemetry.
- A time base / RTOS tick for the fixed-rate control loop (`APP_CONTROL_RATE_HZ`).

## Pin map (fill in)
| Signal | Peripheral / Channel | Pin | Notes |
|--------|----------------------|-----|-------|
| Pan servo PWM  | TIMx_CHx | TBD | 50 Hz; CCR = pulse width (1.0–2.0 ms) |
| Tilt servo PWM | TIMx_CHy | TBD | 50 Hz |
| UART TX (to Jetson RX) | USARTx_TX | TBD | 3.3 V |
| UART RX (from Jetson TX) | USARTx_RX | TBD | 3.3 V |
| GND | — | — | common ground with Jetson **and** servo supply |

## Timer math (to compute once clocks are set)
- PWM period = 20 ms (50 Hz). Pick prescaler+ARR so 1 tick ≈ 1 µs for easy pulse mapping.
- Pulse range from `app_config.h`: MIN/MID/MAX pulse µs → CCR.

## Wiring reminders (see ../../docs/context/hardware.md)
- Servos powered from a **separate 5–6 V supply** (not the Nucleo), common ground.
- Confirm UART voltage levels (3.3 V) before connecting.
