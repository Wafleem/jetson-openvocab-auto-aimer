#ifndef GIMBAL_TELEMETRY_H
#define GIMBAL_TELEMETRY_H

#include <stdbool.h>
#include <stdint.h>

#include "gimbal_messages.h"

#define GIMBAL_TELEMETRY_VERSION    1U
#define GIMBAL_TELEMETRY_FRAME_SIZE 18U
#define GIMBAL_TELEMETRY_CRC_OFFSET 16U

bool GimbalTelemetry_Encode(const GimbalTelemetry *telemetry,
                            uint8_t frame[GIMBAL_TELEMETRY_FRAME_SIZE]);

#endif /* GIMBAL_TELEMETRY_H */
