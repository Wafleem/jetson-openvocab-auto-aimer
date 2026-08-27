#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
ioc_file="$project_dir/jetson-openvocab-autoaim-stm32.ioc"
cube_n6_root="${CUBE_N6_ROOT:-$project_dir/build/vendor/stm32cube-n6}"
cubemx="${CUBEMX:-/Applications/STMicroelectronics/STM32CubeMX.app/Contents/MacOS/STM32CubeMX}"

fail() {
  echo "error: $*" >&2
  exit 1
}

[[ -x "$cubemx" ]] || fail "STM32CubeMX executable not found at $cubemx (or set CUBEMX)"
[[ -f "$cube_n6_root/package.xml" ]] || fail "STM32CubeN6 is missing; run tools/fetch-validation-deps.sh first"

required_version="$(awk -F= '/^MxCube.Version=/{print $2}' "$ioc_file")"
required_family="${required_version%.*}"
installed_family="${CUBEMX_VERSION_FAMILY:-}"

if [[ -z "$installed_family" && "$cubemx" == *.app/Contents/MacOS/STM32CubeMX ]]; then
  app_root="${cubemx%%.app/*}.app"
  installed_family="$(plutil -extract CFBundleShortVersionString raw "$app_root/Contents/Info.plist")"
fi

if [[ -n "$installed_family" && "$installed_family" != "$required_family" ]]; then
  fail "the IOC requires STM32CubeMX $required_version, but $installed_family is installed; use a matching $required_family.x release to avoid an unsafe database migration"
fi

command_file="$(mktemp "${TMPDIR:-/tmp}/stm32-gimbal-cubemx.XXXXXX")"
cleanup() {
  rm -f "$command_file"
}
trap cleanup EXIT

printf '%s\n' \
  "config load \"$ioc_file\"" \
  "project setCustomFWPath \"$cube_n6_root\"" \
  "project generate" \
  "exit" > "$command_file"

cd "$project_dir"
"$cubemx" -q "$command_file"
