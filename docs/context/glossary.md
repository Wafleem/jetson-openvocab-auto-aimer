# Glossary

- **Open-vocabulary detection** — object detection that takes arbitrary text prompts (not a fixed
  class list), so you can detect "the red mug" without retraining.
- **NanoOWL** — NVIDIA's TensorRT-optimized version of OWL-ViT for real-time open-vocab detection on
  Jetson. The perception backbone here.
- **OWL-ViT / OWLv2** — the open-vocab detection model family NanoOWL is based on.
- **PaliGemma** — a vision-language model (VLM) from Google: takes an image + text and outputs text.
  Used here to look at the frame plus the query and choose/refine the target.
- **VLM (vision-language model)** — a model that jointly reasons over images and text.
- **VLA (vision-language-action)** — a model that maps vision+language directly to actions. Considered
  but not chosen; see decisions.md.
- **TensorRT** — NVIDIA's inference runtime; compiles models into optimized `.engine` files for the GPU.
- **STT (speech-to-text)** — converts the spoken query into a text string on the Jetson.
- **Angular error** — yaw/pitch offset from the camera's optical center, in radians. The 2D solver
  derives it from pixel position and calibrated field of view; the Jetson sends it to the STM32.
- **PID** — Proportional-Integral-Derivative controller. Two independent ones here: pan and tilt.
- **Pan / Tilt** — horizontal (yaw) and vertical (pitch) gimbal axes.
- **HAL** — STM32 Hardware Abstraction Layer (CubeMX-generated driver API).
- **CubeMX / `.ioc`** — ST's graphical config tool and its project file describing pins/clocks/peripherals.
- **FreeRTOS** — the real-time OS running the firmware tasks on the STM32.
- **L4T / jetson-containers** — NVIDIA's Linux-for-Tegra base images / container project the Jetson
  Docker image builds on.
