#ifndef GIMBAL_CONTROL_H
#define GIMBAL_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

#include "gimbal_messages.h"

#define GIMBAL_CONTROL_DEFAULT_PERIOD_MS 20U

typedef struct
{
  float minimum_pulse_us;
  float neutral_pulse_us;
  float maximum_pulse_us;
  float maximum_rate_us_s;
  float kp_us_s_per_rad;
  float ki_us_s_per_rad_s;
  float kd_us_per_rad;
  float integral_limit_rad_s;
  float direction;
} GimbalAxisConfig;

typedef struct
{
  GimbalAxisConfig yaw;
  GimbalAxisConfig pitch;
  float period_s;
} GimbalControlConfig;

typedef struct
{
  float setpoint_us;
  float integral_error_rad_s;
  float previous_error_rad;
  bool previous_error_valid;
  bool saturated;
} GimbalAxisState;

typedef struct
{
  GimbalControlConfig config;
  GimbalAxisState yaw;
  GimbalAxisState pitch;
  uint8_t mode;
} GimbalControl;

typedef struct
{
  uint16_t yaw_pulse_us;
  uint16_t pitch_pulse_us;
  uint8_t mode;
  bool yaw_saturated;
  bool pitch_saturated;
} GimbalControlOutput;

GimbalControlConfig GimbalControl_DefaultConfig(void);
bool GimbalControl_Init(GimbalControl *control, const GimbalControlConfig *config);
void GimbalControl_Hold(GimbalControl *control);
void GimbalControl_Step(GimbalControl *control, const GimbalCommand *command);
GimbalControlOutput GimbalControl_GetOutput(const GimbalControl *control);

#endif /* GIMBAL_CONTROL_H */
