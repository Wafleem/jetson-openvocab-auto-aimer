# Jetson: how to run

This folder currently does one thing: use NanoOWL to find text-described objects in a photo.
Run these commands **on the Jetson**, from this folder.

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

The future UART handoff converts that pixel error to yaw/pitch angular error using the calibrated
camera field of view. Raw pixels are not the controller packet.

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
| `Dockerfile` | Installs the Jetson/NanoOWL dependencies. |
| `models/` | Stores the generated TensorRT engine. |

Camera streaming, voice input, PaliGemma, tracking, and UART are intentionally not implemented
yet. Add them one at a time after this static-photo test works on the Jetson.

## Useful commands

```bash
./run.sh help    # show the commands
./run.sh shell   # open a shell inside the container
```

If Docker reports a permission error, add your user to the Docker group or run the same command
from an account with Docker access. `run.sh` also tries `sudo docker` automatically.
