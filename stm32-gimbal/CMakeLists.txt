cmake_minimum_required(VERSION 3.20)

project(stm32_gimbal_host_tests C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

enable_testing()

add_library(gimbal_core STATIC
  App/gimbal_control.c
  App/gimbal_protocol.c
  App/gimbal_telemetry.c
)
target_include_directories(gimbal_core PUBLIC App)

if(MSVC)
  target_compile_options(gimbal_core PRIVATE /W4 /WX)
else()
  target_compile_options(gimbal_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

add_executable(test_gimbal_control tests/test_gimbal_control.c)
target_link_libraries(test_gimbal_control PRIVATE gimbal_core m)
add_test(NAME gimbal_control COMMAND test_gimbal_control)

add_executable(test_gimbal_protocol tests/test_gimbal_protocol.c)
target_link_libraries(test_gimbal_protocol PRIVATE gimbal_core m)
add_test(NAME gimbal_protocol COMMAND test_gimbal_protocol)

add_executable(test_gimbal_telemetry tests/test_gimbal_telemetry.c)
target_link_libraries(test_gimbal_telemetry PRIVATE gimbal_core m)
add_test(NAME gimbal_telemetry COMMAND test_gimbal_telemetry)
