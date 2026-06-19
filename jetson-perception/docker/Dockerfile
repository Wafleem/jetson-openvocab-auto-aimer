# Jetson image for perception bring-up.
# R36 L4T userspace is the latest broadly available nvcr.io tag here; the NVIDIA container runtime
# mounts the host Jetson driver/userspace libraries at launch.
ARG L4T_BASE=nvcr.io/nvidia/l4t-base:r36.2.0
FROM ${L4T_BASE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-venv git build-essential libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Python deps not already in the base image. Do not use --no-cache-dir here; a mounted pip cache
# keeps repeated Jetson builds tolerable.
COPY requirements.txt /workspace/requirements.txt
RUN pip3 install --break-system-packages -r /workspace/requirements.txt

# --- NanoOWL + its torch2trt dependency ---
# Optional because torch2trt/nanoowl can be slow and brittle while iterating on the VLM/text slice.
#   https://github.com/NVIDIA-AI-IOT/torch2trt
#   https://github.com/NVIDIA-AI-IOT/nanoowl
ARG INSTALL_NANOOWL=0
RUN if [ "$INSTALL_NANOOWL" = "1" ]; then \
        pip3 install --break-system-packages git+https://github.com/NVIDIA-AI-IOT/torch2trt \
        && pip3 install --break-system-packages git+https://github.com/NVIDIA-AI-IOT/nanoowl ; \
    fi

COPY . /workspace/jetson-perception
WORKDIR /workspace/jetson-perception
ENV PYTHONPATH=/workspace/jetson-perception/src
RUN pip3 install --break-system-packages -e . --no-deps

# Default to an interactive shell.
CMD ["bash"]
