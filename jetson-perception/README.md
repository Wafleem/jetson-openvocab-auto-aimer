# Jetson: how to run

This folder uses NanoOWL to find open-vocabulary candidates and can use PaliGemma 2 to select the
candidate that matches a more specific visual-language query. Run these commands **on the Jetson**,
from this folder.

This setup targets the Jetson's current JetPack 7 / L4T R39 software.

## First run

```bash
./run.sh setup
./run.sh engine
./run.sh detect path/to/photo.jpg "a person,a red mug"
```

- `setup` builds the Docker container. This is slow the first time.
- `engine` builds `models/owl_image_encoder_patch32.engine`. Do this once.
- `detect` searches one real photo. Separate multiple descriptions with commas.

Later runs only need the `detect` command.

## PaliGemma VLM

PaliGemma is optional for plain NanoOWL detection. To enable it, first accept Google's Gemma license
on the [PaliGemma 2 model page](https://huggingface.co/google/paligemma2-3b-mix-224), then store your
Hugging Face token in the mounted model cache:

```bash
./run.sh model-login
./run.sh vlm path/to/photo.jpg "the red mug"
```

The photo command is the direct hardware/model check: it loads the real 4-bit model on CUDA, asks
PaliGemma to localize the query, and prints the returned pixel boxes. The default model is the 224 px
PaliGemma 2 3B mix checkpoint; the mix checkpoint is intended for use without additional fine-tuning.
The container builds bitsandbytes for the Orin GPU instead of installing the incompatible generic
ARM wheel.

## CSI camera

In Jetson-IO, select the overlay that matches the connector printed on the carrier board:

- `CAM0` uses `Camera IMX219-A`.
- `CAM1` uses `Camera IMX219-C`.

After enabling the overlay and rebooting the Jetson:

```bash
./run.sh camera-check
./run.sh camera "a person,a red mug"
```

`camera-check` only checks whether Linux can see the real sensor; it does not need Docker.
This lets NVIDIA Argus settle its exposure and white balance, saves the final real frame to
`models/camera.jpg`, and runs detection on it. There is no fake camera fallback: the command
stops with an error if the CSI sensor does not produce a frame.
The capture uses Argus's fluorescent white-balance preset, calibrated for this camera and room.
The capture command selects NVIDIA's EGL driver explicitly so desktop Mesa settings cannot
intercept the Argus camera stream.

### Live detection

```bash
./run.sh live "a computer mouse"
```

A local `NanoOWL Live` window opens when the model is ready. NanoOWL automatically locks a
stable detection; click a particular box to choose it instead. The window shows the camera
center, target center, and signed `dx`/`dy` pixel error. Press `R` to release a lost target,
or press `Q`, `Esc`, or close the window to stop it.

Use PaliGemma when NanoOWL has several plausible candidates and the target needs a more specific
description:

```bash
./run.sh live "a mug,a bottle" --vlm-query "the red mug beside the keyboard"
```

While searching, PaliGemma localizes the specific query and its box is associated with a NanoOWL
candidate above the lock threshold. NanoOWL then tracks that precise detector box at the normal
camera rate. PaliGemma runs again after loss, at most once per second by default; change that with
`--vlm-interval SECONDS`. Manual click selection remains available.

The CDC handoff converts that pixel error to yaw/pitch angular error using the calibrated camera
field of view. Raw pixels are not the controller packet.

Once the STM32 firmware enumerates as USB CDC, enable gimbal commands with:

```bash
./run.sh live "a computer mouse" --serial /dev/ttyACM0
```

The Jetson sends a track command only while the tracker is confirmed. It sends hold while searching,
coasting, or lost, and once more when the live program closes.

The initial IMX219 16:9 estimate is `62.2` degrees horizontal by `37.4` degrees vertical. Override
it without changing code while calibrating the clone lens:

```bash
./run.sh live "a computer mouse" --hfov 62.2 --vfov 37.4
```

The default detector confidence is `0.10`, but automatic locking requires `0.50`. Every candidate
box shows its confidence. If the real mouse consistently scores lower, reduce only the lock value:

```bash
./run.sh live "a computer mouse" --lock-threshold 0.40
```

The tracking and future servo handoff are explained in [TRACKING.md](TRACKING.md).

If `camera-check` reports I2C error `-121`, shut down and remove power before reseating the
ribbon. The gold contacts on the Jetson's 22-pin connector must face the board.

## Files

| File | Purpose |
|------|---------|
| `run.sh` | The only command you need to use. |
| `aimer.py` | Builds the engine and runs detection. |
| `vlm_selector.py` | Runs PaliGemma localization and associates its output with NanoOWL boxes. |
| `Dockerfile` | Installs the Jetson/NanoOWL dependencies. |
| `models/` | Stores the generated TensorRT engine. |

Voice input is not implemented yet; queries are supplied as command-line text.

## Useful commands

```bash
./run.sh help    # show the commands
./run.sh shell   # open a shell inside the container
```

If Docker reports a permission error, add your user to the Docker group or run the same command
from an account with Docker access. `run.sh` also tries `sudo docker` automatically.
