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
[UM3354 Rev 3 user manual](https://www.st.com/resource/en/user_manual/um3354-camera-module-for-stm32-boards-stmicroelectronics.pdf),
[MB1854-CSI-B02 schematic](https://www.st.com/resource/en/schematic_pack/mb1854-csi-b02-schematic.pdf),
[ST's IMX335 Linux notes](https://wiki.st.com/stm32mpu/wiki/Camera_sensors_hardware_components), and
[STM32N6570-DK manual](https://www.st.com/resource/en/user_manual/um3300-discovery-kit-with-stm32n657x0-mcu-stmicroelectronics.pdf).

### What ST documents

UM3354 defines CN1 as a **3.3 V signaling** connector with this assignment:

| Pins | Signals |
|------|---------|
| 1, 4, 7, 10, 13, 16, 19 | Ground |
| 2/3 | CSI data lane 0 N/P |
| 5/6 | CSI data lane 1 N/P |
| 8/9 | CSI clock N/P |
| 11/12 | ToF enable/interrupt |
| 14/15 | IMU interrupts 1/2 |
| 17/18 | Camera reset (active low) / module-regulator enable (active high) |
| 20/21 | Shared I2C SCL/SDA |
| 22 | 3.3 V input |

The B02 schematic adds several useful details:

- `EN_MODULE` enables onboard regulators which derive 2.8 V, 1.8 V, and 1.2 V from the 3.3 V input.
- An onboard 24 MHz oscillator supplies the image sensor clock. The host does not need to supply the
  sensor's MCLK through CN1.
- The image sensor I2C side is level-shifted from the shared 3.3 V bus to 1.8 V.
- The image sensor is at 7-bit I2C address `0x1a`.
- ST's Linux device-tree example uses two data lanes and `link-frequencies = <594000000>`.

The manual lists `0xD4` for the IMU and `0x52` for ToF. Those are 8-bit wire-format addresses;
Linux uses the corresponding 7-bit addresses `0x6a` and `0x29`.

### Jetson connection warning

**Do not plug the supplied B-CAMS ribbon directly into the Jetson camera connector yet.** A 22-pin,
0.5 mm connector describes only its mechanical form. ST's assignment includes 3.3 V outputs from
the IMU and ToF plus dedicated enable/reset inputs. It is not the standard Jetson camera-header
assignment, and cable contact orientation can reverse the apparent pin order.

Use a small interposer which has been checked pin-by-pin with a continuity meter. For camera-only
bring-up it must route 3.3 V, ground, I2C, reset, regulator enable, CSI clock, and both CSI data lanes;
leave the four IMU/ToF control and interrupt signals isolated. Route those signals to suitable Jetson
GPIOs separately only when the extra sensors are needed. Confirm whether the module sticker says
`MB1854-CSI-B01` or `MB1854-CSI-B02` before finalizing the adapter.

### STM32/UVC fallback

This is available if direct Jetson CSI bring-up proves impractical; it is not the current plan.

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

Direct IMX335-to-Jetson CSI remains an option, but do not try it by cable shape alone. The installed
Jetson Linux R39.2 kernel reports `CONFIG_VIDEO_IMX335` as disabled, and contains neither an IMX335
module nor an Orin Nano IMX335 overlay. Linux does have a GPL-2.0 IMX335 V4L2 driver:

- The Linux 6.8 version is already named in the installed kernel's Kconfig and Makefile, but its
  source is not installed and that version is hard-coded for four CSI lanes.
- [Current upstream Linux](https://github.com/torvalds/linux/blob/master/drivers/media/i2c/imx335.c)
  supports both two and four lanes. B-CAMS-IMX needs the newer two-lane path.

Do not write the sensor driver from scratch first. The future bring-up should backport the current
upstream driver against NVIDIA's exact R39.2 kernel source, build it as an out-of-tree module, and
create a CAM1 device-tree overlay for the interposer's reset and enable GPIOs, I2C address `0x1a`,
two CSI lanes, and 594 MHz link frequency. Validate raw capture with direct V4L2 before attempting
Argus.

That generic driver does not automatically provide `nvarguscamerasrc` or NVIDIA ISP tuning. Full
Argus use may still require adapting it to NVIDIA's Camera Core interface and tuning the Bayer
pipeline. NVIDIA recommends its Camera Core/Argus path for ISP use and recommends working with a
certified camera partner for Bayer sensor tuning. See NVIDIA's
[camera software guide](https://docs.nvidia.com/jetson/archives/r35.6.2/DeveloperGuide/SD/CameraDevelopment/CameraSoftwareDevelopmentSolution.html)
and [sensor driver guide](https://docs.nvidia.com/jetson/archives/r35.3.1/DeveloperGuide/text/SD/CameraDevelopment/SensorSoftwareDriverProgramming.html).

## Gimbal / actuators
- 2-axis pan-tilt bracket.
- 2× standard hobby servos (50 Hz PWM, ~1.0–2.0 ms pulse → angle). e.g. MG996R / SG90 (TBD).
- Servos need their own power supply (do NOT power from the Nucleo). Common ground with the STM32.

## STM32 peripheral map
| Function | Peripheral | Pin(s) | Notes |
|----------|-----------|--------|-------|
| Pan servo PWM | TIM2 CH1 | PA15 | 50 Hz, 1000–2000 us pulse |
| Tilt servo PWM | TIM2 CH2 | PC0 | 50 Hz, 1000–2000 us pulse |
| Jetson link | USB1 OTG HS, USBX CDC ACM | USB-C | raw SP protocol bytes |
| Control tick | FreeRTOS task | — | 20 ms PID/control period |

## Wiring: Jetson ↔ STM32 USB CDC
- Connect the Nucleo USB-C device port to the Jetson with a data-capable cable.
- The Jetson bridge opens the enumerated CDC ACM device (normally `/dev/ttyACM*`).

## Power notes
- Servos: separate 5–6 V supply sized for stall current.
- Keep servo power transients off the logic supplies.
