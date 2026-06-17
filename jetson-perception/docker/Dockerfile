# Jetson image for NanoOWL bring-up.
# Base on an NVIDIA L4T image that already provides CUDA + TensorRT + PyTorch for your JetPack.
# VERIFY the tag matches your JetPack/L4T before building.
ARG L4T_BASE=nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.2-py3
FROM ${L4T_BASE}

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip git \
    && rm -rf /var/lib/apt/lists/*

# Python deps not already in the base image.
COPY requirements.txt /workspace/requirements.txt
RUN pip3 install --no-cache-dir -r /workspace/requirements.txt

# --- NanoOWL + its torch2trt dependency ---
# TODO: pin versions / follow upstream install notes.
#   https://github.com/NVIDIA-AI-IOT/torch2trt
#   https://github.com/NVIDIA-AI-IOT/nanoowl
RUN pip3 install --no-cache-dir git+https://github.com/NVIDIA-AI-IOT/torch2trt \
    && pip3 install --no-cache-dir git+https://github.com/NVIDIA-AI-IOT/nanoowl

COPY . /workspace/jetson-perception
WORKDIR /workspace/jetson-perception
ENV PYTHONPATH=/workspace/jetson-perception/src

# Default to an interactive shell; build the engine then run aimer.run_detect.
CMD ["bash"]
