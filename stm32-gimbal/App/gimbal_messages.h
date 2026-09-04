#ifndef GIMBAL_MESSAGES_H
#define GIMBAL_MESSAGES_H

#include <stdbool.h>
#include <stdint.h>

typedef struct
{
  uint8_t mode;
  float yaw_error_rad;
  float yaw_velocity_rad_s;
  float yaw_acceleration_rad_s2;
  float pitch_error_rad;
  float pitch_velocity_rad_s;
  float pitch_acceleration_rad_s2;
  uint32_t received_tick_ms;
} GimbalCommand;

#define GIMBAL_TELEMETRY_STATUS_USB_CONNECTED   (1U << 0)
#define GIMBAL_TELEMETRY_STATUS_COMMAND_FRESH   (1U << 1)
#define GIMBAL_TELEMETRY_STATUS_TRACKING_ACTIVE (1U << 2)
#define GIMBAL_TELEMETRY_STATUS_YAW_SATURATED   (1U << 3)
#define GIMBAL_TELEMETRY_STATUS_PITCH_SATURATED (1U << 4)
#define GIMBAL_TELEMETRY_COMMAND_AGE_UNKNOWN    UINT16_MAX

typedef struct
{
  uint8_t mode;
  uint16_t status_flags;
  uint16_t yaw_pulse_us;
  uint16_t pitch_pulse_us;
  uint16_t command_age_ms;
  uint32_t sequence;
} GimbalTelemetry;

bool GimbalMessages_Init(void);
bool GimbalMessages_PublishCommand(const GimbalCommand *command);
bool GimbalMessages_ReadLatestCommand(GimbalCommand *command);
bool GimbalMessages_PublishTelemetry(const GimbalTelemetry *telemetry);
bool GimbalMessages_ReadLatestTelemetry(GimbalTelemetry *telemetry);

#endif /* GIMBAL_MESSAGES_H */
