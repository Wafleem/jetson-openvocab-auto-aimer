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

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-tools \
        kmod \
        libgles2 \
        python3-opencv \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update \
    && apt-get install -y --no-install-recommends libwayland-egl1 \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -m 0700 /tmp/runtime-root

RUN PYTHON_PACKAGES="$(python3 -c \
        'import sysconfig; print(sysconfig.get_paths()["purelib"])')" \
    && NANOOWL_FILE="$PYTHON_PACKAGES/nanoowl/owl_predictor.py" \
    && IMAGE_PREPROCESSOR_FILE="$PYTHON_PACKAGES/nanoowl/image_preprocessor.py" \
    && sed -i \
        '/torch.linspace(0\., 1\., self\.image_size)$/s/$/,\n                indexing="ij"/' \
        "$NANOOWL_FILE" \
    && sed -i \
        's/torch.from_numpy(np.asarray(image))/torch.from_numpy(np.asarray(image).copy())/' \
        "$IMAGE_PREPROCESSOR_FILE"

ENV LD_LIBRARY_PATH=/opt/hpcx/ucx/lib:/opt/hpcx/ucc/lib:${LD_LIBRARY_PATH}
ENV XDG_RUNTIME_DIR=/tmp/runtime-root

WORKDIR /app
COPY aimer.py /app/aimer.py
COPY targeting.py /app/targeting.py
CMD ["bash"]
