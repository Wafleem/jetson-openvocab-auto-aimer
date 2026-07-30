# Tracking and aiming

The live command now performs the three Jetson-side jobs needed before servos exist:

```bash
./run.sh live "a computer mouse"
```

## 1. Keep one target

NanoOWL describes *what* an object is; it does not assign a permanent identity. The
`TargetTracker` in `targeting.py` adds a small state machine:

```text
SEARCHING -> TENTATIVE -> TRACKING -> COASTING -> LOST
```

- A detection must agree twice before it becomes a trusted track.
- The next detection is matched using box overlap, center proximity, and size similarity.
- A constant-velocity estimate predicts brief motion between detections.
- Eight misses are tolerated as `COASTING`, but aim output is paused during those misses.
- `LOST` never silently switches to another similar object. Press `R` to search again.
- When several similar objects are visible, click the desired detection to lock it explicitly.

This follows the same basic association and shadow-tracking concepts documented for NVIDIA
DeepStream trackers, while remaining small enough to understand. It cannot prove identity after
a long, complete occlusion. That later requires appearance features such as NvDCF or Re-ID.

## 2. Calculate where to aim

For a tracked box `(x1, y1, x2, y2)`:

```text
target_x = (x1 + x2) / 2
target_y = (y1 + y2) / 2
dx = target_x - frame_width / 2
dy = target_y - frame_height / 2
```

Positive `dx` means the target is right of center. Positive `dy` means it is below center.
A 20-pixel deadband turns small errors into zero so the future gimbal does not chatter.

`AimSolution` is the future handoff boundary. Only a solution with `valid=True` may be sent to
the microcontroller. The STM32 will receive `dx` and `dy`; it will own PID, angle limits, PWM,
and the motor update rate.

## 3. Detect while moving

The camera source drops old frames, so inference always works from the newest available image.
NanoOWL continues detecting every processed frame while the tracker associates the selected
box. During future gimbal movement:

- Keep servo motion slower than the camera can observe.
- Stop sending movement when the track is `COASTING` or `LOST`.
- Resume only after NanoOWL confirms the same target again.
- Keep the deadband and enforce mechanical limits in the STM32.

No servo data is generated yet because no microcontroller is connected.
