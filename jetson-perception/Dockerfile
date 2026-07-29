# NVIDIA publishes this image for both x86_64 and ARM64 Jetsons. It includes the
# matching CUDA, PyTorch, and TensorRT stack, so we do not assemble those pieces ourselves.
FROM nvcr.io/nvidia/pytorch:25.08-py3

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://repo.download.nvidia.com/jetson/jetson-ota-public.asc \
        | gpg --dearmor > /usr/share/keyrings/nvidia-jetson-ota-public.gpg \
    && printf 'deb [signed-by=/usr/share/keyrings/nvidia-jetson-ota-public.gpg] https://repo.download.nvidia.com/jetson/common r39.2 main\n' \
        > /etc/apt/sources.list.d/nvidia-r39.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends libnvinfer-bin python3-libnvinfer \
    && pip3 uninstall -y tensorrt \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install "transformers<5" onnx \
    && pip3 install --no-build-isolation \
        git+https://github.com/NVIDIA-AI-IOT/torch2trt@4e820ae31b4e35d59685935223b05b2e11d47b03 \
    && TORCH2TRT_FILE="$(python3 -c \
        'import importlib.util; print(importlib.util.find_spec("torch2trt").submodule_search_locations[0] + "/dataset_calibrator.py")')" \
    && sed -i \
        's/if trt.__version__ >=/if not hasattr(trt, "CalibrationAlgoType"):\n    DEFAULT_CALIBRATION_ALGORITHM = None\nelif trt.__version__ >=/' \
        "$TORCH2TRT_FILE" \
    && sed -i \
        's/class DatasetCalibrator(trt.IInt8Calibrator):/class DatasetCalibrator(getattr(trt, "IInt8Calibrator", object)):/' \
        "$TORCH2TRT_FILE" \
    && pip3 install \
        git+https://github.com/NVIDIA-AI-IOT/nanoowl@fb553dee4c58f8c53ec2bf01f355a54648e67dbd \
    && NANOOWL_FILE="$(python3 -c \
        'import inspect, nanoowl.owl_predictor; print(inspect.getfile(nanoowl.owl_predictor))')" \
    && sed -i 's/opset_version=onnx_opset/opset_version=onnx_opset,\n            dynamo=False/' \
        "$NANOOWL_FILE"

WORKDIR /app
COPY aimer.py /app/aimer.py
CMD ["bash"]
