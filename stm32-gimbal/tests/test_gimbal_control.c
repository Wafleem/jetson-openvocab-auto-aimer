#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "../App/gimbal_control.h"

static GimbalCommand Command(uint8_t mode, float yaw_error_rad, float pitch_error_rad)
{
  GimbalCommand command = {0};

  command.mode = mode;
  command.yaw_error_rad = yaw_error_rad;
  command.pitch_error_rad = pitch_error_rad;
  return command;
}

static void TestInitializesAtNeutral(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalControlOutput output;

  assert(GimbalControl_Init(&control, &config));
  output = GimbalControl_GetOutput(&control);
  assert(output.yaw_pulse_us == 1500U);
  assert(output.pitch_pulse_us == 1500U);
  assert(output.mode == 0U);
  assert(!output.yaw_saturated);
  assert(!output.pitch_saturated);
}

static void TestRejectsInvalidConfiguration(void)
{
  GimbalControl control;
  GimbalControlConfig config = GimbalControl_DefaultConfig();

  assert(!GimbalControl_Init(NULL, &config));
  assert(!GimbalControl_Init(&control, NULL));

  config.period_s = 0.0F;
  assert(!GimbalControl_Init(&control, &config));
  config = GimbalControl_DefaultConfig();
  config.yaw.neutral_pulse_us = config.yaw.maximum_pulse_us;
  assert(!GimbalControl_Init(&control, &config));
  config = GimbalControl_DefaultConfig();
  config.pitch.direction = 0.0F;
  assert(!GimbalControl_Init(&control, &config));
}

static void TestAxesMoveIndependentlyWithExpectedSigns(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalCommand command = Command(1U, -0.25F, 0.125F);
  GimbalControlOutput output;

  assert(GimbalControl_Init(&control, &config));
  GimbalControl_Step(&control, &command);
  output = GimbalControl_GetOutput(&control);
  assert(output.yaw_pulse_us < 1500U);
  assert(output.pitch_pulse_us > 1500U);
  assert(output.mode == 1U);
}

static void TestRateLimitBoundsEveryControlStep(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalCommand command = Command(1U, 3.0F, -3.0F);
  GimbalControlOutput output;

  assert(GimbalControl_Init(&control, &config));
  GimbalControl_Step(&control, &command);
  output = GimbalControl_GetOutput(&control);

  /* 800 us/s for a 20 ms step permits at most 16 us of movement. */
  assert(output.yaw_pulse_us == 1516U);
  assert(output.pitch_pulse_us == 1484U);
  assert(output.yaw_saturated);
  assert(output.pitch_saturated);
}

static void TestMechanicalLimitsAndAntiWindup(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalCommand command = Command(1U, 3.0F, 3.0F);
  GimbalControlOutput output;

  assert(GimbalControl_Init(&control, &config));
  for (size_t step = 0U; step < 200U; ++step)
  {
    GimbalControl_Step(&control, &command);
    output = GimbalControl_GetOutput(&control);
    assert(output.yaw_pulse_us <= 2000U);
    assert(output.pitch_pulse_us <= 2000U);
  }
  assert(output.yaw_pulse_us == 2000U);
  assert(output.pitch_pulse_us == 2000U);
  assert(output.yaw_saturated);
  assert(output.pitch_saturated);
  assert(control.yaw.integral_error_rad_s < config.yaw.integral_limit_rad_s);
  assert(control.pitch.integral_error_rad_s < config.pitch.integral_limit_rad_s);

  command.yaw_error_rad = -3.0F;
  command.pitch_error_rad = -3.0F;
  GimbalControl_Step(&control, &command);
  output = GimbalControl_GetOutput(&control);
  assert(output.yaw_pulse_us < 2000U);
  assert(output.pitch_pulse_us < 2000U);
}

static void TestHoldRetainsPositionAndClearsPidHistory(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalCommand command = Command(1U, 0.5F, -0.5F);
  GimbalControlOutput moving;
  GimbalControlOutput holding;

  assert(GimbalControl_Init(&control, &config));
  for (size_t step = 0U; step < 10U; ++step)
  {
    GimbalControl_Step(&control, &command);
  }
  moving = GimbalControl_GetOutput(&control);
  assert(fabsf(control.yaw.integral_error_rad_s) > 0.0F);
  assert(control.yaw.previous_error_valid);

  command = Command(0U, 3.0F, 3.0F);
  GimbalControl_Step(&control, &command);
  holding = GimbalControl_GetOutput(&control);
  assert(holding.yaw_pulse_us == moving.yaw_pulse_us);
  assert(holding.pitch_pulse_us == moving.pitch_pulse_us);
  assert(holding.mode == 0U);
  assert(control.yaw.integral_error_rad_s == 0.0F);
  assert(control.pitch.integral_error_rad_s == 0.0F);
  assert(!control.yaw.previous_error_valid);
  assert(!control.pitch.previous_error_valid);
}

static void TestNullCommandIsTimeoutHold(void)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalCommand command = Command(2U, 0.25F, 0.25F);
  GimbalControlOutput moving;
  GimbalControlOutput holding;

  assert(GimbalControl_Init(&control, &config));
  GimbalControl_Step(&control, &command);
  moving = GimbalControl_GetOutput(&control);
  GimbalControl_Step(&control, NULL);
  holding = GimbalControl_GetOutput(&control);
  assert(holding.yaw_pulse_us == moving.yaw_pulse_us);
  assert(holding.pitch_pulse_us == moving.pitch_pulse_us);
  assert(holding.mode == 0U);
}

int main(void)
{
  TestInitializesAtNeutral();
  TestRejectsInvalidConfiguration();
  TestAxesMoveIndependentlyWithExpectedSigns();
  TestRateLimitBoundsEveryControlStep();
  TestMechanicalLimitsAndAntiWindup();
  TestHoldRetainsPositionAndClearsPidHistory();
  TestNullCommandIsTimeoutHold();
  puts("gimbal control tests passed");
  return 0;
}
