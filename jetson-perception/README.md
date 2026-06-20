# jetson-perception

Jetson Orin Nano 8GB perception. NanoOWL TensorRT bring-up and text-command parsing are
implemented. Camera streaming, voice, control-target, and UART integration remain deferred;
see the root [../AGENTS.md](../AGENTS.md) and [../docs/](../docs/) for the full system design.

## NanoOWL bring-up

```bash
cd jetson-perception
AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh
# inside the container:
python scripts/build_engine.py --output /models/owl_image_encoder_patch32.engine
python -m aimer.run_detect \
    --engine /models/owl_image_encoder_patch32.engine \
    --image /workspace/jetson-perception/path/to/frame.jpg \
    --prompts "a person, a red mug"
```

For the lighter text-command/PaliGemma slice, leave NanoOWL out of the build:

```bash
cd docker && ./run.sh aimer-command-parse --backend heuristic "track the red mug"
cd docker && ./run.sh aimer-paligemma-preflight --model-id google/paligemma2-3b-mix-224
```

`docker/run.sh` mounts `models/`, the host Hugging Face cache, and the host pip cache. It also
passes `HF_TOKEN` through if that environment variable is set.

## Text command parsing
The first text-only piece of the later voice pipeline turns natural commands into NanoOWL-ready
object prompts:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

```bash
python -m aimer.command_parse --backend heuristic "track the red mug"
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
PaliGemma. PaliGemma requires a real camera frame or photo:

```bash
AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh aimer-command-parse \
    --backend paligemma \
    --model-id google/paligemma2-3b-mix-224 \
    --image /workspace/jetson-perception/path/to/frame.jpg \
    "aim at the small red mug near the laptop"
```

The first PaliGemma run downloads the checkpoint into the mounted Hugging Face cache. Its JSON
`primary_prompt` is ready for NanoOWL; spatial context remains separate for later target
selection.

If installed editable in a venv, the console script is also available:

```bash
aimer-command-parse --backend heuristic "track the red mug"
```

Spatial relations such as `near the laptop` are returned as metadata for later target selection
rather than being folded into the NanoOWL object prompt.

Check local PaliGemma prerequisites and Hugging Face model access without downloading the full
checkpoint:

```bash
python -m aimer.paligemma_preflight --model-id google/paligemma2-3b-mix-224
```

If installed editable in a venv:

```bash
aimer-paligemma-preflight --model-id google/paligemma2-3b-mix-224
```

Google PaliGemma checkpoints require accepting model terms on Hugging Face and authenticating the
Jetson before weights can be downloaded. The preflight verifies model access, Transformers support,
and CUDA visibility without downloading the full checkpoint. Keep `transformers<5` for now;
Transformers 5.x failed to resolve the PaliGemma image processor in this environment.

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

**Status:** NanoOWL static-image detection and text-command parsing are ready for hardware testing.
