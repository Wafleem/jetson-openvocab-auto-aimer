# jetson-perception

Jetson Orin Nano 8GB perception. **Current milestone: get NanoOWL running** (open-vocab
detection on TensorRT). The rest of the pipeline (PaliGemma VLM, voice, control-target, UART
to the gimbal) is deferred — see the root [../AGENTS.md](../AGENTS.md) and [../docs/](../docs/)
for the full system design.

## NanoOWL bring-up
```bash
cd docker && ./run.sh                          # build image + drop into a shell
# inside the container:
python scripts/build_engine.py                 # build the TensorRT engine -> /models
python -m aimer.run_detect \
    --engine /models/owl_image_encoder_patch32.engine \
    --image test.jpg --prompts "a person, a red mug"
```

## Layout
- `src/aimer/detector.py` — NanoOWL wrapper (`NanoOwlDetector`).
- `src/aimer/run_detect.py` — CLI smoke test: detect prompts in one image.
- `scripts/build_engine.py` — build the NanoOWL TensorRT engine.
- `docker/` — Dockerfile (L4T + NanoOWL) and `run.sh`.
- `models/` — engines/weights (gitignored).

**Status:** scaffold — `detector.py` internals are TODO. See [AGENTS.md](AGENTS.md).
