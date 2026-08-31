# jetson-openvocab-auto-aimer

A voice-driven, open-vocabulary auto-aiming camera gimbal for the Jetson Orin Nano and STM32N6.

Speak a target such as "the red mug." The Jetson detects open-vocabulary candidates, uses a
PaliGemma vision-language model (VLM) to select the requested object, tracks its position, and sends
angular error to the STM32. The STM32 runs the real-time servo controller and returns status
telemetry over the same USB connection.

```text
CSI camera + target query
          |
          v
NanoOWL TensorRT detection -> PaliGemma target selection -> angular error solver
          |                                                   |
          +---------------- live target lock -----------------+
                                                              |
                                                29-byte SP command + CRC-16
                                                              |
                                                              v
                                      STM32N657 USB CDC + FreeRTOS
                                                              |
                                     two-axis PID -> 50 Hz pan/tilt PWM
                                                              |
                                                status telemetry to Jetson
```

## Implementation

### Jetson perception and target selection

The Jetson runtime is in [`jetson-perception/`](jetson-perception/). It uses a JetPack 7 / L4T R39
Docker image and keeps the GPU model environment separate from the host system.

- NVIDIA Argus supplies frames from an IMX219 or IMX477 CSI camera.
- NanoOWL runs its image encoder as a TensorRT engine and produces open-vocabulary candidate boxes.
- PaliGemma 2 3B Mix runs on CUDA with 4-bit NF4 quantization. It converts the specific VLM query to
  normalized localization tokens.
- `vlm_selector.py` converts those tokens to image coordinates and associates them with NanoOWL
  boxes by overlap and center proximity. NanoOWL then tracks the selected detector box at camera
  rate. PaliGemma performs target selection again after a lost lock.
- `targeting.py` converts the target-center offset to yaw and pitch angular error with the calibrated
  horizontal and vertical camera field of view.
- `gimbal_link.py` encodes the angular error as the project SP command, writes it to the USB CDC
  device, and decodes asynchronous STM32 telemetry.

Start the live VLM-assisted tracker on the Jetson:

```bash
cd jetson-perception
./run.sh setup
./run.sh engine
./run.sh model-login
./run.sh live "a mug,a bottle" --vlm-query "the red mug" --serial /dev/ttyACM0
```

The tracker sends `track` only for a confirmed target. Search, coast, loss, and shutdown send
`hold`. Camera field-of-view values and target-lock thresholds are command-line options, so lens
calibration does not require a code change.

### STM32N6 gimbal controller

The firmware is in [`stm32-gimbal/`](stm32-gimbal/). The CubeMX project targets the
STM32N657X0H3Q and divides the runtime into the standard STM32N6 TrustZone contexts:

- `FSBL/` initializes external memory and loads the secure and non-secure application images.
- `AppS/` configures the Resource Isolation Framework (RIF), makes the command-link and PWM
  peripherals non-secure, and transfers control to the non-secure application.
- `AppNS/` owns USBX CDC ACM, USB Power Delivery (USB-PD), FreeRTOS, TIM14, and TIM16.
- `App/` contains the handwritten protocol, message queue, controller, telemetry, and application
  tasks. CubeMX regeneration preserves this directory.

The USB task accepts fragmented input, finds the `SP` header, validates CRC-16, and publishes the
newest valid command through a FreeRTOS queue. The 20 ms controller task runs independent yaw and
pitch positional PID loops. The controller includes integral anti-windup, derivative reset on hold,
servo rate limits, mechanical pulse limits, and a 250 ms command watchdog. TIM14 CH1 on PG2 and
TIM16 CH1 on PA3 generate the two 50 Hz servo signals.

The STM32 publishes telemetry every 100 ms. Each telemetry frame reports controller mode, USB and
command state, saturation flags, commanded pulse widths, command age, sequence number, and CRC-16.

### USB protocol

The protocol is defined in [`docs/uart-protocol.md`](docs/uart-protocol.md) and implemented in both
Python and C.

| Direction | Frame | Contents |
| --- | ---: | --- |
| Jetson to STM32 | 29 bytes | `SP`, mode, six little-endian floats, CRC-16 |
| STM32 to Jetson | 18 bytes | `ST`, version, mode, flags, pulse widths, age, sequence, CRC-16 |

Yaw and pitch fields contain continuous angular error in radians. They are not raw pixels or
one-time position increments.

## Build and validation

The checked-in implementation passes 21 Jetson protocol and targeting tests, three
sanitizer-backed C firmware suites, compilation of all 40 Cortex-M55 translation units, and complete
FSBL, AppS, and AppNS image linkage.

Run the Jetson-side protocol, targeting, tracker, and VLM association tests on a development host:

```bash
cd jetson-perception
python3 -m unittest discover -s tests -v
```

Run the sanitizer-backed controller tests and compile all STM32 translation units for Cortex-M55:

```bash
cd stm32-gimbal
./tools/fetch-validation-deps.sh
ARM_GCC=/path/to/arm-none-eabi-gcc ./tools/validate.sh
ARM_GCC=/path/to/arm-none-eabi-gcc ./tools/build-target.sh
```

The target build links `fsbl.elf`, `app_s.elf`, and `app_ns.elf`, and emits the matching binary
images under `stm32-gimbal/build/target/`. Use `tools/sign-images.sh` to add the STM32 secure-boot
headers before programming external flash with STM32CubeProgrammer.

## Repository layout

- [`jetson-perception/`](jetson-perception/) — Dockerized NanoOWL, PaliGemma, tracking, and USB link.
- [`stm32-gimbal/`](stm32-gimbal/) — CubeMX/HAL, FreeRTOS, USB CDC, PID, telemetry, and PWM firmware.
- [`docs/`](docs/) — architecture, SP protocol, hardware notes, and design decisions.
