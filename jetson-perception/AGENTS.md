# AGENTS.md - Jetson side

Read the root `../AGENTS.md` first.

## Current milestone

Get NanoOWL working on one real photo. Do not add camera streaming, voice, PaliGemma, tracking,
or UART until this milestone works on the Jetson.

The complete beginner-facing workflow is:

```bash
./run.sh setup
./run.sh engine
./run.sh detect path/to/photo.jpg "a person,a red mug"
```

## Files

- `run.sh`: host-side Docker commands.
- `Dockerfile`: Jetson dependencies.
- `aimer.py`: the complete Python program for this milestone.
- `models/`: generated TensorRT engine; do not commit it.

Keep this structure small. When the next hardware milestone starts, add only the code required for
that milestone. Heavy imports belong inside functions so `python3 aimer.py --help` works without the
Jetson libraries installed.

No mock or simulated data. Test against real Jetson hardware and real images.
