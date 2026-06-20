# jetson-perception

Jetson Orin Nano 8GB perception. NanoOWL TensorRT bring-up and text-command parsing are
implemented. Camera streaming, voice, control-target, and UART integration remain deferred;
see the root [../AGENTS.md](../AGENTS.md) and [../docs/](../docs/) for the full system design.

## NanoOWL bring-up

```bash
cd jetson-perception
AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh
# inside the container:
python3 scripts/build_engine.py --output /models/owl_image_encoder_patch32.engine
python3 -m aimer.run_detect \
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

The command parser turns a natural-language camera command into a compact object description that
NanoOWL can detect. It removes action words and conversational filler, preserves useful visual
attributes, and separates spatial context for the later target-selection stage.

### Quick start: container

Run this from `jetson-perception/` on the Jetson:

```bash
cd /home/safal/Documents/jetson-openvocab-auto-aimer/jetson-perception

AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh \
    aimer-command-parse --backend heuristic \
    "uh, could you please point the camera at the small red mug beside the laptop?"
```

The first invocation checks/builds the image; Docker reuses its cached layers afterward. The
`heuristic` backend is deterministic, does not download a model, and is the recommended way to
exercise the parser by itself.

Example output:

```json
{
  "attributes": ["small", "red"],
  "confidence": 0.55,
  "nanoowl_prompts": ["a small red mug", "small red mug"],
  "notes": [
    "Spatial context kept out of NanoOWL prompt for later target selection."
  ],
  "parser": "heuristic",
  "primary_prompt": "a small red mug",
  "raw_command": "uh, could you please point the camera at the small red mug beside the laptop?",
  "spatial_context": "beside the laptop",
  "target_phrase": "small red mug"
}
```

The important fields are:

- `primary_prompt`: the preferred text prompt to pass to NanoOWL.
- `nanoowl_prompts`: the preferred prompt followed by useful fallback wording.
- `target_phrase`: the extracted visual object without an added article.
- `attributes`: visual details retained from the command, such as color, size, or material.
- `spatial_context`: relationships kept out of the detector prompt for later target selection.
- `parser`: identifies whether the heuristic or PaliGemma backend produced the result.

Try a few command styles:

```bash
AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh \
    aimer-command-parse --backend heuristic "track the green bottle"

AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh \
    aimer-command-parse --backend heuristic "follow the person in the blue shirt"

AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh \
    aimer-command-parse --backend heuristic \
    "um, can you like focus on the large silver thermos near the monitor?"
```

### Local development

The lightweight parser can also run outside Docker. From `jetson-perception/`:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m aimer.command_parse --backend heuristic "track the red mug"
```

The editable install also provides the shorter console command:

```bash
aimer-command-parse --backend heuristic "track the red mug"
```

### Parser backends

- `--backend heuristic` always uses the fast deterministic parser.
- `--backend paligemma` requires local PaliGemma inference and fails if it cannot run.
- `--backend auto` tries PaliGemma first and reports a heuristic fallback in `notes` if unavailable.

PaliGemma must receive a real camera frame or photograph because it is an image-and-text model:

```bash
AIMER_IMAGE=aimer:nanoowl INSTALL_NANOOWL=1 ./docker/run.sh aimer-command-parse \
    --backend paligemma \
    --model-id google/paligemma2-3b-mix-224 \
    --image /workspace/jetson-perception/path/to/frame.jpg \
    "aim at the small red mug near the laptop"
```

The first PaliGemma run downloads the checkpoint into the mounted Hugging Face cache. Its JSON
`primary_prompt` is ready for NanoOWL; spatial context remains separate for later target
selection. The PaliGemma path is currently a hardware test path; the heuristic parser is the
validated standalone demonstration.

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
