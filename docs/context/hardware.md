# Hardware

> Fill in concrete part numbers, pins, and ports as the rig is assembled. Values marked TBD/example
> are placeholders.

## Compute
- **Jetson Orin Nano Developer Kit, 8 GB** — runs perception (NanoOWL + PaliGemma) under Docker.
- **STM32N6 Nucleo dev board** — runs gimbal firmware (FreeRTOS). Lean motor-controller role;
  the Neural-ART NPU is unused for now.

## Camera
- Current camera: Arducam-clone IMX219 on physical CAM1, exposed by Argus as sensor ID 0.
- Accessed via GStreamer `nvarguscamerasrc` at 1280x720.

## Optional ST B-CAMS-IMX module

If the label says `B-CAMS-IMX` or `MB1854`, this is the camera bundled with the STM32N6570-DK.
It contains:

- Sony IMX335 5-Mpixel RGB rolling-shutter sensor, dual-lane MIPI CSI-2.
- Manual-focus M12 lens, 3.24 mm focal length, f/2.7, 87-degree field of view.
- ISM330DLC 6-axis IMU: 3-axis accelerometer plus 3-axis gyroscope.
- VL53L5CX direct Time-of-Flight sensor with 4x4 or 8x8 distance zones.
- One shared 3.3 V, 22-pin FFC connection carrying MIPI, I2C, interrupts, reset, and power control.

Official references: [ST product page](https://www.st.com/en/evaluation-tools/b-cams-imx.html),
[UM3354 user manual](https://www.st.com/resource/en/user_manual/dm01077940.pdf), and
[STM32N6570-DK manual](https://www.st.com/resource/en/user_manual/um3300-discovery-kit-with-stm32n657x0-mcu-stmicroelectronics.pdf).

### Recommended integration order

1. Keep the working IMX219 on the Jetson while target tracking is developed.
2. Connect B-CAMS-IMX to the STM32N6 camera connector, not directly to the Jetson. Start with an
   official STM32CubeN6 DCMIPP example and verify that `IMX335_Probe()` reads the sensor ID.
3. Try ST's NUCLEO-N657X0-Q USB/UVC example. Connected over USB, it can appear to the Jetson as a
   normal `/dev/video*` camera. A future Jetson input can use `v4l2src`; Argus is not used for UVC.
4. Read the IMU on the STM32 over I2C using its interrupt/FIFO support. Calibrate gyro bias while
   stationary, map its axes to pan and tilt, and mount it rigidly to the moving camera plate.
5. Use angular velocity as fast stabilization feedback or PID feed-forward. Continue using Jetson
   `dx`/`dy` as the target-position command. The IMU measures camera motion, not target identity.
6. Add ToF only after tracking and servos work. It can supply target-range or proximity information,
   but its coarse zones must be aligned with the RGB image before associating a range with a box.

The alternative is connecting IMX335 directly to Jetson CSI. Do not try that by cable shape alone.
NVIDIA's default image does not include this module's driver. Direct use requires verifying every
pin and voltage, adding an IMX335 V4L2 sensor driver and device-tree overlay, and performing Bayer
ISP image-quality tuning. NVIDIA recommends its Camera Core/Argus path for ISP use and recommends
working with a certified camera partner for Bayer sensor tuning. See NVIDIA's
[camera software guide](https://docs.nvidia.com/jetson/archives/r35.6.2/DeveloperGuide/SD/CameraDevelopment/CameraSoftwareDevelopmentSolution.html)
and [sensor driver guide](https://docs.nvidia.com/jetson/archives/r35.3.1/DeveloperGuide/text/SD/CameraDevelopment/SensorSoftwareDriverProgramming.html).

Note: ST's manuals print the I2C addresses in 8-bit form (`0xD4` for the IMU and `0x52` for ToF).
Linux and most modern drivers use 7-bit addresses: `0x6A` for ISM330DLC and `0x29` for VL53L5CX.

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
