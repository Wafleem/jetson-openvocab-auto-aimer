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
- Automatic acquisition requires `0.50` confidence; weaker `0.10` detections remain visible but
  cannot start a track.
- The next detection is matched using box overlap, center proximity, and size similarity.
- A constant-velocity estimate predicts brief motion between detections.
- Eight misses are tolerated as `COASTING`, but aim output is paused during those misses.
- `LOST` never silently switches to another similar object. Press `R` to search again.
- When several similar objects are visible, click the desired detection to lock it explicitly.

This follows the same basic association and shadow-tracking concepts documented for NVIDIA
DeepStream trackers, while remaining small enough to understand. It cannot prove identity after
a long, complete occlusion. That later requires appearance features such as NvDCF or Re-ID.

### The momentary-drop filter

`BoxFilter` is a small alpha-beta filter. Think of it as two alternating steps:

1. **Predict:** move the previous box by its estimated velocity.
2. **Correct:** when NanoOWL supplies a box, move the prediction toward that measurement and
   update the velocity from the remaining error.

If NanoOWL misses a frame, the filter uses the prediction instead. Velocity is bounded and reduced
by 40% on every missed frame so the box settles rather than flying across the image. The overlay
then shows `COASTING prediction N/8`. A new matching measurement corrects the prediction and
returns the track to `TRACKING`; the ninth consecutive miss changes it to `LOST`.

`LOST` can reacquire, but only when a new detection exceeds the lock threshold and remains near
the last filtered box. That strong detection moves the same track ID to `TENTATIVE`; one more
matching frame restores `TRACKING`. A far-away lookalike is ignored until you click it or press
`R` to begin a new search.

The predicted box helps association, but it does not create a valid aim command. This distinction
is intentional: a future motor may follow measured-and-filtered positions, but should not continue
moving toward a target that the camera cannot currently see.

Do not raise both confidence values at once. Tune `--lock-threshold` first so random objects cannot
start a track. Keep `--threshold` lower so an already selected target can survive weaker frames.

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

Before UART transmission, the calibrated 2D solver converts pixel error into angular error:

```text
yaw_error   = -atan((dx / half_width)  * tan(horizontal_fov / 2))
pitch_error =  atan((dy / half_height) * tan(vertical_fov / 2))
```

`AimSolution` is the future handoff boundary. Only a solution with `valid=True` may be sent to
the microcontroller. The STM32 will receive yaw/pitch error offsets in radians; it will own PID,
angle limits, PWM, and the motor update rate.

## 3. Detect while moving

The camera source drops old frames, so inference always works from the newest available image.
NanoOWL continues detecting every processed frame while the tracker associates the selected
box. During future gimbal movement:

- Keep servo motion slower than the camera can observe.
- Stop sending movement when the track is `COASTING` or `LOST`.
- Resume only after NanoOWL confirms the same target again.
- Keep the deadband and enforce mechanical limits in the STM32.

No servo data is generated yet because no microcontroller is connected.
