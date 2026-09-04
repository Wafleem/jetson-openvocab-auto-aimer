#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
input_dir="${TARGET_BUILD_DIR:-$project_dir/build/target}"
output_dir="${SIGNED_BUILD_DIR:-$input_dir/signed}"
signing_tool="${STM32_SIGNING_TOOL:-STM32_SigningTool_CLI}"

fail() {
  echo "error: $*" >&2
  exit 1
}

command -v "$signing_tool" >/dev/null 2>&1 || \
  fail "STM32 SigningTool CLI is required (or set STM32_SIGNING_TOOL)"

for image in fsbl app_s app_ns; do
  [[ -f "$input_dir/$image.bin" ]] || \
    fail "missing $input_dir/$image.bin; run tools/build-target.sh first"
done

mkdir -p "$output_dir"

for image in fsbl app_s app_ns; do
  "$signing_tool" \
    -bin "$input_dir/$image.bin" \
    -nk \
    -of 0x80000000 \
    -t fsbl \
    -o "$output_dir/$image-trusted.bin" \
    -hv 2.3
done

echo "Signed STM32 images: $output_dir"
