#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
cd "$project_dir"

cube_root="${CUBE_N6_ROOT:-$project_dir/build/vendor/stm32cube-n6}"
freertos_root="${X_CUBE_FREERTOS_ROOT:-$project_dir/build/vendor/x-cube-freertos}"
arm_gcc="${ARM_GCC:-arm-none-eabi-gcc}"
host_build_dir="${HOST_BUILD_DIR:-$project_dir/build/host-validation}"

fail() {
  echo "error: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "missing $1; run tools/fetch-validation-deps.sh first"
}

require_literal() {
  local literal="$1"
  local path="$2"
  grep -Fq "$literal" "$path" || fail "$path is missing: $literal"
}

command -v cmake >/dev/null 2>&1 || fail "cmake is required"
command -v "$arm_gcc" >/dev/null 2>&1 || fail "Arm GNU arm-none-eabi-gcc is required (or set ARM_GCC)"

require_file "$cube_root/Drivers/STM32N6xx_HAL_Driver/Inc/stm32n6xx_hal.h"
require_file "$cube_root/Drivers/CMSIS/Device/ST/STM32N6xx/Include/stm32n657xx.h"
require_file "$cube_root/Middlewares/ST/usbx/common/core/inc/ux_api.h"
require_file "$cube_root/Middlewares/ST/STM32_USBPD_Library/Core/inc/usbpd_core.h"
require_file "$freertos_root/Middlewares/Third_Party/FreeRTOS/Source/include/FreeRTOS.h"
require_file "$freertos_root/Drivers/CMSIS/RTOS2/Include/cmsis_os2.h"

ioc="jetson-openvocab-autoaim-stm32.ioc"
require_literal "PG2.Signal=S_TIM14_CH1" "$ioc"
require_literal "PA3.Signal=S_TIM16_CH1" "$ioc"
require_literal "TIM14.Prescaler=399" "$ioc"
require_literal "TIM14.PeriodNoDither=19999" "$ioc"
require_literal "TIM16.Prescaler=399" "$ioc"
require_literal "TIM16.PeriodNoDither=19999" "$ioc"
require_literal "MX_USBPD_Init-USBPD-true-HAL-false-AppliNonSecure" "$ioc"

if grep -R -E -q 'htim2|MX_TIM2|S_TIM2|PA15\(JTDI\)|TIM2_CH' App AppNS "$ioc"; then
  fail "obsolete TIM2 servo routing remains in the runtime project"
fi

cmake -S . -B "$host_build_dir" \
  -DCMAKE_C_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -Wall -Wextra -Wpedantic -Werror"
cmake --build "$host_build_dir" --clean-first
ctest --test-dir "$host_build_dir" --output-on-failure

object_dir="$(mktemp -d "${TMPDIR:-/tmp}/stm32-gimbal-objects.XXXXXX")"
cleanup_object_dir() {
  if [[ -d "$object_dir" ]]; then
    rm -r -- "$object_dir"
  fi
}
trap cleanup_object_dir EXIT

hal_root="$cube_root/Drivers/STM32N6xx_HAL_Driver"
cmsis_root="$cube_root/Drivers/CMSIS"
extmem_root="$cube_root/Middlewares/ST/STM32_ExtMem_Manager"
freertos_source="$freertos_root/Middlewares/Third_Party/FreeRTOS/Source"
usbx_root="$cube_root/Middlewares/ST/usbx"
usbpd_root="$cube_root/Middlewares/ST/STM32_USBPD_Library"

base_flags=(
  -mcpu=cortex-m55
  -mthumb
  -std=c11
  -ffreestanding
  -ffunction-sections
  -fdata-sections
  -Wall
  -Wextra
  -Wpedantic
  -Werror
  -Wno-unused-parameter
  -DSTM32N657xx
  -DUSE_HAL_DRIVER
  -DUSE_FULL_LL_DRIVER
  -I"$hal_root/Inc"
  -I"$hal_root/Inc/Legacy"
  -I"$cmsis_root/Device/ST/STM32N6xx/Include"
  -I"$cmsis_root/Include"
)

nonsecure_flags=(
  -IApp
  -IAppNS/Inc
  -ISecure_nsclib
  -I"$freertos_source/include"
  -I"$freertos_source/portable/GCC/ARM_CM55/non_secure"
  -I"$freertos_source/CMSIS_RTOS_V2"
  -I"$freertos_root/Drivers/CMSIS/RTOS2/Include"
  -I"$usbx_root/common/core/inc"
  -I"$usbx_root/common/usbx_device_classes/inc"
  -I"$usbx_root/common/usbx_stm32_device_controllers"
  -I"$usbx_root/common/usbx_stm32_config"
  -I"$usbx_root/ports/generic/inc"
  -I"$usbpd_root/Core/inc"
  -I"$usbpd_root/Devices/STM32N6XX/inc"
  -DUX_INCLUDE_USER_DEFINE_FILE
  -DUSBPD_PORT_COUNT=1
  -DUSBPDCORE_LIB_NO_PD
  -D_SNK
)

secure_flags=(
  -mcmse
  -IAppS/Inc
  -ISecure_nsclib
)

fsbl_flags=(
  -mcmse
  -IFSBL/Inc
  -I"$extmem_root"
  -I"$extmem_root/sal"
  -I"$extmem_root/boot"
  -I"$extmem_root/nor_sfdp"
)

compile_tree() {
  local context="$1"
  local source_dir="$2"
  shift 2
  local context_flags=("$@")
  local count=0
  local source

  while IFS= read -r -d '' source; do
    count=$((count + 1))
    "$arm_gcc" "${base_flags[@]}" "${context_flags[@]}" \
      -c "$source" -o "$object_dir/$context-$count.o"
  done < <(find "$source_dir" -type f -name '*.c' -print0)

  echo "Arm object compilation passed: $context ($count translation units)"
}

printf '#include <string.h>\nint main(void) { return 0; }\n' | \
  "$arm_gcc" -mcpu=cortex-m55 -mthumb -x c -c - -o "$object_dir/toolchain-smoke.o"

compile_tree app App "${nonsecure_flags[@]}"
compile_tree appns AppNS/Src "${nonsecure_flags[@]}"
compile_tree apps AppS/Src "${secure_flags[@]}"
compile_tree fsbl FSBL/Src "${fsbl_flags[@]}"

echo "STM32 validation passed."
