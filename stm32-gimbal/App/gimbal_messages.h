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

bool GimbalMessages_Init(void);
bool GimbalMessages_PublishCommand(const GimbalCommand *command);
bool GimbalMessages_ReadLatestCommand(GimbalCommand *command);

#endif /* GIMBAL_MESSAGES_H */
