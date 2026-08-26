#include "gimbal_telemetry.h"

#include <stddef.h>

#include "gimbal_protocol.h"

#define GIMBAL_TELEMETRY_HEADER_0 ((uint8_t)'S')
#define GIMBAL_TELEMETRY_HEADER_1 ((uint8_t)'T')

static void GimbalTelemetry_WriteU16Le(uint8_t *destination, uint16_t value)
{
  destination[0] = (uint8_t)value;
  destination[1] = (uint8_t)(value >> 8U);
}

static void GimbalTelemetry_WriteU32Le(uint8_t *destination, uint32_t value)
{
  destination[0] = (uint8_t)value;
  destination[1] = (uint8_t)(value >> 8U);
  destination[2] = (uint8_t)(value >> 16U);
  destination[3] = (uint8_t)(value >> 24U);
}

bool GimbalTelemetry_Encode(const GimbalTelemetry *telemetry,
                            uint8_t frame[GIMBAL_TELEMETRY_FRAME_SIZE])
{
  uint16_t crc;

  if ((telemetry == NULL) || (frame == NULL) || (telemetry->mode > 2U))
  {
    return false;
  }

  frame[0] = GIMBAL_TELEMETRY_HEADER_0;
  frame[1] = GIMBAL_TELEMETRY_HEADER_1;
  frame[2] = GIMBAL_TELEMETRY_VERSION;
  frame[3] = telemetry->mode;
  GimbalTelemetry_WriteU16Le(&frame[4], telemetry->status_flags);
  GimbalTelemetry_WriteU16Le(&frame[6], telemetry->yaw_pulse_us);
  GimbalTelemetry_WriteU16Le(&frame[8], telemetry->pitch_pulse_us);
  GimbalTelemetry_WriteU16Le(&frame[10], telemetry->command_age_ms);
  GimbalTelemetry_WriteU32Le(&frame[12], telemetry->sequence);
  crc = GimbalProtocol_Crc16(frame, GIMBAL_TELEMETRY_CRC_OFFSET);
  GimbalTelemetry_WriteU16Le(&frame[GIMBAL_TELEMETRY_CRC_OFFSET], crc);
  return true;
}
