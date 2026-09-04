#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
cd "$project_dir"

cube_root="${CUBE_N6_ROOT:-$project_dir/build/vendor/stm32cube-n6}"
freertos_root="${X_CUBE_FREERTOS_ROOT:-$project_dir/build/vendor/x-cube-freertos}"
arm_gcc="${ARM_GCC:-arm-none-eabi-gcc}"
target_dir="${TARGET_BUILD_DIR:-$project_dir/build/target}"
object_dir="$target_dir/objects"

fail() {
  echo "error: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "missing $1; run tools/fetch-validation-deps.sh first"
}

arm_gcc_path="$(command -v "$arm_gcc")" || fail "Arm GNU arm-none-eabi-gcc is required (or set ARM_GCC)"
arm_tool_dir="$(cd "$(dirname "$arm_gcc_path")" && pwd)"
arm_objcopy="${ARM_OBJCOPY:-$arm_tool_dir/arm-none-eabi-objcopy}"
arm_size="${ARM_SIZE:-$arm_tool_dir/arm-none-eabi-size}"
arm_readelf="${ARM_READELF:-$arm_tool_dir/arm-none-eabi-readelf}"
command -v "$arm_objcopy" >/dev/null 2>&1 || fail "Arm GNU arm-none-eabi-objcopy is required (or set ARM_OBJCOPY)"
command -v "$arm_size" >/dev/null 2>&1 || fail "Arm GNU arm-none-eabi-size is required (or set ARM_SIZE)"
command -v "$arm_readelf" >/dev/null 2>&1 || fail "Arm GNU arm-none-eabi-readelf is required (or set ARM_READELF)"

hal_root="$cube_root/Drivers/STM32N6xx_HAL_Driver"
cmsis_root="$cube_root/Drivers/CMSIS"
device_root="$cmsis_root/Device/ST/STM32N6xx"
extmem_root="$cube_root/Middlewares/ST/STM32_ExtMem_Manager"
freertos_source="$freertos_root/Middlewares/Third_Party/FreeRTOS/Source"
usbx_root="$cube_root/Middlewares/ST/usbx"
usbpd_root="$cube_root/Middlewares/ST/STM32_USBPD_Library"

require_file "$device_root/Source/Templates/gcc/startup_stm32n657xx.s"
require_file "$device_root/Source/Templates/gcc/linker/STM32N657XX_LRUN_s.ld"
require_file "$device_root/Source/Templates/gcc/linker/STM32N657XX_LRUN_ns.ld"
require_file "$device_root/Source/Templates/gcc/linker/STM32N657XX_AXISRAM2_fsbl.ld"
require_file "$usbpd_root/Core/lib/USBPDCORE_NOPD_CM55_wc32.a"

mkdir -p "$object_dir"

common_flags=(
  -mcpu=cortex-m55
  -mthumb
  -std=gnu11
  -Os
  -g3
  -ffunction-sections
  -fdata-sections
  -fno-common
  -DSTM32N657xx
  -DUSE_HAL_DRIVER
  -DUSE_FULL_LL_DRIVER
  -I"$hal_root/Inc"
  -I"$hal_root/Inc/Legacy"
  -I"$device_root/Include"
  -I"$cmsis_root/Include"
)

secure_flags=(
  -mcmse
  -IAppS/Inc
  -ISecure_nsclib
  -I"$freertos_source/include"
  -I"$freertos_source/portable/GCC/ARM_CM55/secure"
)

nonsecure_flags=(
  -IApp
  -IAppNS/Inc
  -ISecure_nsclib
  -I"$freertos_source/include"
  -I"$freertos_source/portable/GCC/ARM_CM55/non_secure"
  -I"$freertos_source/portable/GCC/ARM_CM55/secure"
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

fsbl_flags=(
  -mcmse
  -IFSBL/Inc
  -I"$extmem_root"
  -I"$extmem_root/sal"
  -I"$extmem_root/boot"
  -I"$extmem_root/nor_sfdp"
)

object_counter=0
last_object=""
compile_source() {
  local context="$1"
  local source="$2"
  shift 2
  local flags=("$@")

  object_counter=$((object_counter + 1))
  last_object="$object_dir/$context-$object_counter.o"
  "$arm_gcc" "${common_flags[@]}" "${flags[@]}" -c "$source" -o "$last_object"
}

append_tree() {
  local context="$1"
  local source_dir="$2"
  local destination_name="$3"
  shift 3
  local flags=("$@")
  local source

  while IFS= read -r -d '' source; do
    compile_source "$context" "$source" "${flags[@]}"
    eval "$destination_name+=(\"\$last_object\")"
  done < <(find "$source_dir" -type f -name '*.c' -print0)
}

hal_common=(
  "$hal_root/Src/stm32n6xx_hal.c"
  "$hal_root/Src/stm32n6xx_hal_cortex.c"
  "$hal_root/Src/stm32n6xx_hal_dma.c"
  "$hal_root/Src/stm32n6xx_hal_dma_ex.c"
  "$hal_root/Src/stm32n6xx_hal_exti.c"
  "$hal_root/Src/stm32n6xx_hal_gpio.c"
  "$hal_root/Src/stm32n6xx_hal_pwr.c"
  "$hal_root/Src/stm32n6xx_hal_pwr_ex.c"
  "$hal_root/Src/stm32n6xx_hal_rcc.c"
  "$hal_root/Src/stm32n6xx_hal_rcc_ex.c"
)

app_s_objects=()
append_tree apps AppS/Src app_s_objects "${secure_flags[@]}"
app_s_sources=(
  "$device_root/Source/Templates/system_stm32n6xx_s.c"
  "$device_root/Source/Templates/gcc/startup_stm32n657xx.s"
  "${hal_common[@]}"
  "$hal_root/Src/stm32n6xx_hal_rif.c"
  "$freertos_source/portable/GCC/ARM_CM55/secure/secure_context.c"
  "$freertos_source/portable/GCC/ARM_CM55/secure/secure_context_port.c"
  "$freertos_source/portable/GCC/ARM_CM55/secure/secure_heap.c"
  "$freertos_source/portable/GCC/ARM_CM55/secure/secure_init.c"
)
for source in "${app_s_sources[@]}"; do
  compile_source apps "$source" "${secure_flags[@]}"
  app_s_objects+=("$last_object")
done

secure_import="$target_dir/app_s_import.o"
app_s_elf="$target_dir/app_s.elf"
"$arm_gcc" -mcpu=cortex-m55 -mthumb -mcmse \
  -T"$device_root/Source/Templates/gcc/linker/STM32N657XX_LRUN_s.ld" \
  -Wl,--gc-sections -Wl,--cmse-implib -Wl,--out-implib="$secure_import" \
  -Wl,-Map="$target_dir/app_s.map" --specs=nano.specs --specs=nosys.specs \
  "${app_s_objects[@]}" -Wl,--start-group -lc -lm -lgcc -lnosys -Wl,--end-group -o "$app_s_elf"
"$arm_objcopy" -O binary "$app_s_elf" "$target_dir/app_s.bin"

app_ns_objects=()
append_tree appns App app_ns_objects "${nonsecure_flags[@]}"
append_tree appns AppNS/Src app_ns_objects "${nonsecure_flags[@]}"
app_ns_sources=(
  "$device_root/Source/Templates/system_stm32n6xx_ns.c"
  "$device_root/Source/Templates/gcc/startup_stm32n657xx.s"
  "${hal_common[@]}"
  "$hal_root/Src/stm32n6xx_hal_pcd.c"
  "$hal_root/Src/stm32n6xx_hal_pcd_ex.c"
  "$hal_root/Src/stm32n6xx_hal_tim.c"
  "$hal_root/Src/stm32n6xx_hal_tim_ex.c"
  "$hal_root/Src/stm32n6xx_ll_ucpd.c"
  "$hal_root/Src/stm32n6xx_ll_usb.c"
  "$freertos_source/event_groups.c"
  "$freertos_source/list.c"
  "$freertos_source/queue.c"
  "$freertos_source/stream_buffer.c"
  "$freertos_source/tasks.c"
  "$freertos_source/timers.c"
  "$freertos_source/portable/GCC/ARM_CM55/non_secure/port.c"
  "$freertos_source/portable/GCC/ARM_CM55/non_secure/portasm.c"
  "$freertos_source/portable/MemMang/heap_4.c"
  "$freertos_source/CMSIS_RTOS_V2/cmsis_os2.c"
)
for source in "${app_ns_sources[@]}"; do
  compile_source appns "$source" "${nonsecure_flags[@]}"
  app_ns_objects+=("$last_object")
done
append_tree appns "$usbx_root/common/core/src" app_ns_objects "${nonsecure_flags[@]}"

while IFS= read -r -d '' source; do
  compile_source appns "$source" "${nonsecure_flags[@]}"
  app_ns_objects+=("$last_object")
done < <(find "$usbx_root/common/usbx_device_classes/src" -type f -name 'ux_device_class_cdc_acm*.c' -print0)

append_tree appns "$usbx_root/common/usbx_stm32_device_controllers" app_ns_objects "${nonsecure_flags[@]}"
append_tree appns "$usbpd_root/Devices/STM32N6XX/src" app_ns_objects "${nonsecure_flags[@]}"

app_ns_elf="$target_dir/app_ns.elf"
"$arm_gcc" -mcpu=cortex-m55 -mthumb \
  -T"$device_root/Source/Templates/gcc/linker/STM32N657XX_LRUN_ns.ld" \
  -Wl,--gc-sections -Wl,-Map="$target_dir/app_ns.map" \
  --specs=nano.specs --specs=nosys.specs \
  "${app_ns_objects[@]}" "$secure_import" \
  -Wl,--start-group "$usbpd_root/Core/lib/USBPDCORE_NOPD_CM55_wc32.a" \
  -lc -lm -lgcc -lnosys -Wl,--end-group -o "$app_ns_elf"
"$arm_objcopy" -O binary "$app_ns_elf" "$target_dir/app_ns.bin"

fsbl_objects=()
append_tree fsbl FSBL/Src fsbl_objects "${fsbl_flags[@]}"
fsbl_sources=(
  "$device_root/Source/Templates/system_stm32n6xx_fsbl.c"
  "$device_root/Source/Templates/gcc/startup_stm32n657xx_fsbl.s"
  "${hal_common[@]}"
  "$hal_root/Src/stm32n6xx_hal_bsec.c"
  "$hal_root/Src/stm32n6xx_hal_xspi.c"
  "$extmem_root/stm32_extmem.c"
  "$extmem_root/sal/stm32_sal_xspi.c"
  "$extmem_root/nor_sfdp/stm32_sfdp_data.c"
  "$extmem_root/nor_sfdp/stm32_sfdp_driver.c"
  "$extmem_root/boot/stm32_boot_lrun.c"
)
for source in "${fsbl_sources[@]}"; do
  compile_source fsbl "$source" "${fsbl_flags[@]}"
  fsbl_objects+=("$last_object")
done

fsbl_elf="$target_dir/fsbl.elf"
"$arm_gcc" -mcpu=cortex-m55 -mthumb -mcmse \
  -T"$device_root/Source/Templates/gcc/linker/STM32N657XX_AXISRAM2_fsbl.ld" \
  -Wl,--gc-sections -Wl,-Map="$target_dir/fsbl.map" \
  --specs=nano.specs --specs=nosys.specs \
  "${fsbl_objects[@]}" -Wl,--start-group -lc -lm -lgcc -lnosys -Wl,--end-group -o "$fsbl_elf"
"$arm_objcopy" -O binary "$fsbl_elf" "$target_dir/fsbl.bin"

verify_image() {
  local label="$1"
  local elf="$2"
  local binary="$3"
  local range_start="$4"
  local range_end="$5"
  local slot_size="$6"
  local entry
  local binary_size

  entry="$("$arm_readelf" -h "$elf" | awk '/Entry point address:/ {print $4}')"
  binary_size="$(wc -c < "$binary" | tr -d ' ')"
  if (( entry < range_start || entry >= range_end )); then
    fail "$label entry point $entry is outside its linker range"
  fi
  if (( binary_size > slot_size )); then
    fail "$label binary is $binary_size bytes; slot limit is $slot_size bytes"
  fi
}

verify_image fsbl "$fsbl_elf" "$target_dir/fsbl.bin" 0x34180400 0x341C0000 0x100000
verify_image app_s "$app_s_elf" "$target_dir/app_s.bin" 0x34000400 0x34100000 0x80000
verify_image app_ns "$app_ns_elf" "$target_dir/app_ns.bin" 0x24100400 0x24180000 0x80000

"$arm_size" "$fsbl_elf" "$app_s_elf" "$app_ns_elf"
echo "STM32 target build passed: $target_dir"
