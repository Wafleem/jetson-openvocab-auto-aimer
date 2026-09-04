#include "gimbal_control.h"

#include <math.h>
#include <stddef.h>

#define GIMBAL_CONTROL_PERIOD_S \
  ((float)GIMBAL_CONTROL_DEFAULT_PERIOD_MS / 1000.0F)
#define GIMBAL_SERVO_NEUTRAL_US         1500.0F
#define GIMBAL_SERVO_MIN_US             1000.0F
#define GIMBAL_SERVO_MAX_US             2000.0F
#define GIMBAL_SERVO_MAX_RATE_US_S       800.0F
#define GIMBAL_AXIS_KP_US_S_PER_RAD       650.0F
#define GIMBAL_AXIS_KI_US_S_PER_RAD_S     100.0F
#define GIMBAL_AXIS_KD_US_PER_RAD           5.0F
#define GIMBAL_INTEGRAL_LIMIT_RAD_S          1.0F

static float GimbalControl_Clamp(float value, float minimum, float maximum)
{
  if (value < minimum)
  {
    return minimum;
  }
  if (value > maximum)
  {
    return maximum;
  }
  return value;
}

static bool GimbalControl_AxisConfigIsValid(const GimbalAxisConfig *config)
{
  return (config != NULL) &&
         isfinite(config->minimum_pulse_us) &&
         isfinite(config->neutral_pulse_us) &&
         isfinite(config->maximum_pulse_us) &&
         isfinite(config->maximum_rate_us_s) &&
         isfinite(config->kp_us_s_per_rad) &&
         isfinite(config->ki_us_s_per_rad_s) &&
         isfinite(config->kd_us_per_rad) &&
         isfinite(config->integral_limit_rad_s) &&
         isfinite(config->direction) &&
         (config->minimum_pulse_us < config->neutral_pulse_us) &&
         (config->neutral_pulse_us < config->maximum_pulse_us) &&
         (config->maximum_rate_us_s > 0.0F) &&
         (config->kp_us_s_per_rad >= 0.0F) &&
         (config->ki_us_s_per_rad_s >= 0.0F) &&
         (config->kd_us_per_rad >= 0.0F) &&
         (config->integral_limit_rad_s >= 0.0F) &&
         (fabsf(config->direction) == 1.0F);
}

static void GimbalControl_ResetAxis(GimbalAxisState *axis, float neutral_pulse_us)
{
  axis->setpoint_us = neutral_pulse_us;
  axis->integral_error_rad_s = 0.0F;
  axis->previous_error_rad = 0.0F;
  axis->previous_error_valid = false;
  axis->saturated = false;
}

static void GimbalControl_HoldAxis(GimbalAxisState *axis)
{
  axis->integral_error_rad_s = 0.0F;
  axis->previous_error_rad = 0.0F;
  axis->previous_error_valid = false;
  axis->saturated = false;
}

static float GimbalControl_Rate(const GimbalAxisConfig *config,
                                float error_rad,
                                float integral_error_rad_s,
                                float derivative_rad_s)
{
  return config->direction *
         ((config->kp_us_s_per_rad * error_rad) +
          (config->ki_us_s_per_rad_s * integral_error_rad_s) +
          (config->kd_us_per_rad * derivative_rad_s));
}

static void GimbalControl_StepAxis(GimbalAxisState *axis,
                                   const GimbalAxisConfig *config,
                                   float error_rad,
                                   float period_s)
{
  float derivative_rad_s = 0.0F;
  float candidate_integral;
  float unclamped_rate;
  float rate;
  float candidate_setpoint;
  float integral_output_delta;
  bool rate_saturated;
  bool position_saturated;
  bool reject_integral;

  if (axis->previous_error_valid)
  {
    derivative_rad_s = (error_rad - axis->previous_error_rad) / period_s;
  }

  candidate_integral = GimbalControl_Clamp(
      axis->integral_error_rad_s + (error_rad * period_s),
      -config->integral_limit_rad_s,
      config->integral_limit_rad_s);
  unclamped_rate = GimbalControl_Rate(config,
                                      error_rad,
                                      candidate_integral,
                                      derivative_rad_s);
  rate = GimbalControl_Clamp(unclamped_rate,
                             -config->maximum_rate_us_s,
                             config->maximum_rate_us_s);
  candidate_setpoint = axis->setpoint_us + (rate * period_s);
  rate_saturated = rate != unclamped_rate;
  position_saturated = (candidate_setpoint < config->minimum_pulse_us) ||
                       (candidate_setpoint > config->maximum_pulse_us);
  integral_output_delta = config->direction * config->ki_us_s_per_rad_s *
                          (candidate_integral - axis->integral_error_rad_s);
  reject_integral = (integral_output_delta != 0.0F) &&
                    (((unclamped_rate > 0.0F) && (integral_output_delta > 0.0F)) ||
                     ((unclamped_rate < 0.0F) && (integral_output_delta < 0.0F))) &&
                    (rate_saturated || position_saturated);

  /* Do not accumulate integral while it pushes farther into an actuator limit. */
  if (reject_integral)
  {
    candidate_integral = axis->integral_error_rad_s;
    unclamped_rate = GimbalControl_Rate(config,
                                        error_rad,
                                        candidate_integral,
                                        derivative_rad_s);
    rate = GimbalControl_Clamp(unclamped_rate,
                               -config->maximum_rate_us_s,
                               config->maximum_rate_us_s);
    candidate_setpoint = axis->setpoint_us + (rate * period_s);
    rate_saturated = rate != unclamped_rate;
    position_saturated = (candidate_setpoint < config->minimum_pulse_us) ||
                         (candidate_setpoint > config->maximum_pulse_us);
  }

  axis->integral_error_rad_s = candidate_integral;
  axis->previous_error_rad = error_rad;
  axis->previous_error_valid = true;
  axis->setpoint_us = GimbalControl_Clamp(candidate_setpoint,
                                          config->minimum_pulse_us,
                                          config->maximum_pulse_us);
  axis->saturated = rate_saturated || position_saturated;
}

static uint16_t GimbalControl_RoundPulse(float pulse_us)
{
  return (uint16_t)(pulse_us + 0.5F);
}

GimbalControlConfig GimbalControl_DefaultConfig(void)
{
  const GimbalAxisConfig axis = {
      GIMBAL_SERVO_MIN_US,
      GIMBAL_SERVO_NEUTRAL_US,
      GIMBAL_SERVO_MAX_US,
      GIMBAL_SERVO_MAX_RATE_US_S,
      GIMBAL_AXIS_KP_US_S_PER_RAD,
      GIMBAL_AXIS_KI_US_S_PER_RAD_S,
      GIMBAL_AXIS_KD_US_PER_RAD,
      GIMBAL_INTEGRAL_LIMIT_RAD_S,
      1.0F};
  GimbalControlConfig config = {axis, axis, GIMBAL_CONTROL_PERIOD_S};

  return config;
}

bool GimbalControl_Init(GimbalControl *control, const GimbalControlConfig *config)
{
  if ((control == NULL) || (config == NULL) ||
      !isfinite(config->period_s) || (config->period_s <= 0.0F) ||
      !GimbalControl_AxisConfigIsValid(&config->yaw) ||
      !GimbalControl_AxisConfigIsValid(&config->pitch))
  {
    return false;
  }

  control->config = *config;
  GimbalControl_ResetAxis(&control->yaw, config->yaw.neutral_pulse_us);
  GimbalControl_ResetAxis(&control->pitch, config->pitch.neutral_pulse_us);
  control->mode = 0U;
  return true;
}

void GimbalControl_Hold(GimbalControl *control)
{
  if (control != NULL)
  {
    GimbalControl_HoldAxis(&control->yaw);
    GimbalControl_HoldAxis(&control->pitch);
    control->mode = 0U;
  }
}

void GimbalControl_Step(GimbalControl *control, const GimbalCommand *command)
{
  if (control == NULL)
  {
    return;
  }
  if ((command == NULL) || (command->mode == 0U))
  {
    GimbalControl_Hold(control);
    return;
  }

  GimbalControl_StepAxis(&control->yaw,
                         &control->config.yaw,
                         command->yaw_error_rad,
                         control->config.period_s);
  GimbalControl_StepAxis(&control->pitch,
                         &control->config.pitch,
                         command->pitch_error_rad,
                         control->config.period_s);
  control->mode = command->mode;
}

GimbalControlOutput GimbalControl_GetOutput(const GimbalControl *control)
{
  GimbalControlOutput output = {0U, 0U, 0U, false, false};

  if (control != NULL)
  {
    output.yaw_pulse_us = GimbalControl_RoundPulse(control->yaw.setpoint_us);
    output.pitch_pulse_us = GimbalControl_RoundPulse(control->pitch.setpoint_us);
    output.mode = control->mode;
    output.yaw_saturated = control->yaw.saturated;
    output.pitch_saturated = control->pitch.saturated;
  }
  return output;
}
