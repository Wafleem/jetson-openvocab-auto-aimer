#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
vendor_dir="${1:-$project_dir/build/vendor}"

cube_url="https://github.com/STMicroelectronics/STM32CubeN6.git"
cube_tag="v1.2.0"
cube_commit="85170d2c6eaa438622ed879caa4d7bcc6cc3920d"
freertos_url="https://github.com/STMicroelectronics/x-cube-freertos.git"
freertos_tag="v1.3.1"
freertos_commit="5e43eb05d54c3f237e36a435160767e7d7b34881"

require_git_revision() {
  local checkout_dir="$1"
  local expected_commit="$2"
  local actual_commit

  actual_commit="$(git -C "$checkout_dir" rev-parse HEAD)"
  if [[ "$actual_commit" != "$expected_commit" ]]; then
    echo "error: $checkout_dir is at $actual_commit; expected $expected_commit" >&2
    exit 1
  fi
}

mkdir -p "$vendor_dir"

cube_dir="$vendor_dir/stm32cube-n6"
if [[ ! -d "$cube_dir/.git" ]]; then
  git clone --filter=blob:none --depth 1 --branch "$cube_tag" --no-checkout "$cube_url" "$cube_dir"
  git -C "$cube_dir" sparse-checkout init --cone
  git -C "$cube_dir" sparse-checkout set \
    Drivers/CMSIS \
    Drivers/STM32N6xx_HAL_Driver \
    Middlewares/ST/STM32_ExtMem_Manager \
    Middlewares/ST/STM32_USBPD_Library \
    Middlewares/ST/usbx
  git -C "$cube_dir" checkout --detach "$cube_tag"
  git -C "$cube_dir" submodule update --init --depth 1 \
    Drivers/CMSIS/Device/ST/STM32N6xx \
    Drivers/STM32N6xx_HAL_Driver
fi
require_git_revision "$cube_dir" "$cube_commit"

freertos_dir="$vendor_dir/x-cube-freertos"
if [[ ! -d "$freertos_dir/.git" ]]; then
  git clone --filter=blob:none --depth 1 --branch "$freertos_tag" --no-checkout "$freertos_url" "$freertos_dir"
  git -C "$freertos_dir" sparse-checkout init --cone
  git -C "$freertos_dir" sparse-checkout set \
    Drivers/CMSIS/RTOS2/Include \
    Middlewares/Third_Party/FreeRTOS/Source
  git -C "$freertos_dir" checkout --detach "$freertos_tag"
fi
require_git_revision "$freertos_dir" "$freertos_commit"

echo "STM32 validation dependencies are ready:"
echo "  CUBE_N6_ROOT=$cube_dir"
echo "  X_CUBE_FREERTOS_ROOT=$freertos_dir"
