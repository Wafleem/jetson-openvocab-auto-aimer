# AGENTS.md - Jetson side

Read the root `../AGENTS.md` first.

## Current milestone

NanoOWL camera tracking and the 2D angular solver work on the Jetson. The current milestone is the
real USB CDC handoff to the STM32 gimbal. Voice and PaliGemma remain deferred.

The complete beginner-facing workflow is:

```bash
./run.sh setup
./run.sh engine
./run.sh detect path/to/photo.jpg "a person,a red mug"
./run.sh camera "a person,a red mug"
./run.sh live "a computer mouse"
./run.sh live "a computer mouse" --serial /dev/ttyACM0
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
