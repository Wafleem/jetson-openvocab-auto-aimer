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

## Text command parsing
The first text-only piece of the later voice pipeline turns natural commands into NanoOWL-ready
object prompts:

```bash
PYTHONPATH=src python -m aimer.command_parse --backend heuristic "track the red mug"
```

Output is JSON. `primary_prompt` is the first prompt to feed NanoOWL, and `nanoowl_prompts`
contains fallbacks:

```json
{
  "primary_prompt": "a red mug",
  "target_phrase": "red mug",
  "nanoowl_prompts": ["a red mug", "red mug"]
}
```

Use `--backend auto` to prefer the local PaliGemma backend when model dependencies and weights are
available, falling back to the deterministic parser otherwise. Use `--backend paligemma` to require
PaliGemma:

```bash
PYTHONPATH=src python -m aimer.command_parse --backend paligemma \
    --model-id google/paligemma2-3b-mix-224 \
    "aim at the small red mug near the laptop"
```

Spatial relations such as `near the laptop` are returned as metadata for later target selection
rather than being folded into the NanoOWL object prompt.

## Tests
From `jetson-perception/`:

```bash
python -m pytest -q
```

## Layout
- `src/aimer/detector.py` — NanoOWL wrapper (`NanoOwlDetector`).
- `src/aimer/run_detect.py` — CLI smoke test: detect prompts in one image.
- `src/aimer/command_parse.py` — CLI: parse a text command into NanoOWL prompts.
- `src/aimer/commands/` — command parsing package, including deterministic and PaliGemma backends.
- `scripts/build_engine.py` — build the NanoOWL TensorRT engine.
- `docker/` — Dockerfile (L4T + NanoOWL) and `run.sh`.
- `models/` — engines/weights (gitignored).

**Status:** scaffold — `detector.py` internals are TODO. See [AGENTS.md](AGENTS.md).
