# Jetson image for perception bring-up.
# R36 L4T userspace is the latest broadly available nvcr.io tag here; the NVIDIA container runtime
# mounts the host Jetson driver/userspace libraries at launch.
ARG L4T_BASE=nvcr.io/nvidia/l4t-base:r36.2.0
FROM ${L4T_BASE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace

RUN printf "deb https://repo.download.nvidia.com/jetson/t234 r36.2 main\n" \
        > /etc/apt/sources.list.d/nvidia-t234.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-venv git build-essential libopenblas-dev \
        python3-libnvinfer python3-libnvinfer-dev \
        libnvinfer-dev libnvinfer-plugin-dev libnvonnxparsers-dev \
    && apt-get download nvidia-l4t-dla-compiler \
    && dpkg-deb -x nvidia-l4t-dla-compiler_*.deb / \
    && rm -f nvidia-l4t-dla-compiler_*.deb \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --upgrade pip setuptools wheel

# Python deps not already in the base image. Do not use --no-cache-dir here; a mounted pip cache
# keeps repeated Jetson builds tolerable.
COPY requirements.txt /workspace/requirements.txt
RUN pip3 install -r /workspace/requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends \
        libcudla-12-2 libnvinfer-bin \
    && printf "/usr/lib/aarch64-linux-gnu/nvidia\n" \
        > /etc/ld.so.conf.d/nvidia-l4t.conf \
    && ldconfig \
    && rm -rf /var/lib/apt/lists/*

# --- NanoOWL + its torch2trt dependency ---
# Optional because torch2trt/nanoowl can be slow and brittle while iterating on the VLM/text slice.
#   https://github.com/NVIDIA-AI-IOT/torch2trt
#   https://github.com/NVIDIA-AI-IOT/nanoowl
ARG INSTALL_NANOOWL=0
RUN if [ "$INSTALL_NANOOWL" = "1" ]; then \
        pip3 install onnx torchvision \
        && mkdir -p /tmp/tensorrt-metadata \
        && printf '__version__ = "8.6.2"\n' > /tmp/tensorrt-metadata/tensorrt.py \
        && PYTHONPATH=/tmp/tensorrt-metadata \
            pip3 install --no-build-isolation git+https://github.com/NVIDIA-AI-IOT/torch2trt@4e820ae31b4e35d59685935223b05b2e11d47b03 \
        && rm -rf /tmp/tensorrt-metadata \
        && pip3 install git+https://github.com/NVIDIA-AI-IOT/nanoowl@fb553dee4c58f8c53ec2bf01f355a54648e67dbd \
        && sed -i 's/opset_version=onnx_opset/opset_version=onnx_opset,\n            dynamo=False/' \
            /usr/local/lib/python3.10/dist-packages/nanoowl/owl_predictor.py ; \
    fi

COPY . /workspace/jetson-perception
WORKDIR /workspace/jetson-perception
ENV PYTHONPATH=/workspace/jetson-perception/src
RUN pip3 install -e . --no-deps

# Default to an interactive shell.
CMD ["bash"]
