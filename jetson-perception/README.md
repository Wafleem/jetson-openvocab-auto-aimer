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

After enabling the IMX219 camera overlay and rebooting the Jetson:

```bash
./run.sh camera-check
./run.sh camera "a person,a red mug"
```

`camera-check` only checks whether Linux can see the real sensor; it does not need Docker.
This captures one real frame to `models/camera.jpg` and runs detection on it. There is no fake
camera fallback: the command stops with an error if the CSI sensor does not produce a frame.

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
