# NVIDIA publishes this image for both x86_64 and ARM64 Jetsons. It includes the
# matching CUDA, PyTorch, and TensorRT stack, so we do not assemble those pieces ourselves.
FROM nvcr.io/nvidia/pytorch:26.06-py3

ENV PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip3 install "transformers<5" onnx \
    && pip3 install --no-build-isolation \
        git+https://github.com/NVIDIA-AI-IOT/torch2trt@4e820ae31b4e35d59685935223b05b2e11d47b03 \
    && pip3 install \
        git+https://github.com/NVIDIA-AI-IOT/nanoowl@fb553dee4c58f8c53ec2bf01f355a54648e67dbd \
    && NANOOWL_FILE="$(python3 -c \
        'import inspect, nanoowl.owl_predictor; print(inspect.getfile(nanoowl.owl_predictor))')" \
    && sed -i 's/opset_version=onnx_opset/opset_version=onnx_opset,\n            dynamo=False/' \
        "$NANOOWL_FILE"

WORKDIR /app
COPY aimer.py /app/aimer.py
CMD ["bash"]
