#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../App/gimbal_protocol.h"
#include "../App/gimbal_telemetry.h"

static uint16_t ReadU16Le(const uint8_t *source)
{
  return (uint16_t)source[0] | ((uint16_t)source[1] << 8U);
}

static uint32_t ReadU32Le(const uint8_t *source)
{
  return (uint32_t)source[0] |
         ((uint32_t)source[1] << 8U) |
         ((uint32_t)source[2] << 16U) |
         ((uint32_t)source[3] << 24U);
}

static void TestEncodesDocumentedLayout(void)
{
  static const uint8_t expected[GIMBAL_TELEMETRY_FRAME_SIZE] = {
      0x53U, 0x54U, 0x01U, 0x01U, 0x07U, 0x00U,
      0xC3U, 0x05U, 0xF5U, 0x05U, 0x11U, 0x00U,
      0x78U, 0x56U, 0x34U, 0x12U, 0x05U, 0x8AU};
  const GimbalTelemetry telemetry = {
      1U,
      GIMBAL_TELEMETRY_STATUS_USB_CONNECTED |
          GIMBAL_TELEMETRY_STATUS_COMMAND_FRESH |
          GIMBAL_TELEMETRY_STATUS_TRACKING_ACTIVE,
      1475U,
      1525U,
      17U,
      0x12345678U};
  uint8_t frame[GIMBAL_TELEMETRY_FRAME_SIZE];

  memset(frame, 0xA5, sizeof(frame));
  assert(GimbalTelemetry_Encode(&telemetry, frame));
  assert(sizeof(frame) == 18U);
  assert(frame[0] == (uint8_t)'S');
  assert(frame[1] == (uint8_t)'T');
  assert(frame[2] == GIMBAL_TELEMETRY_VERSION);
  assert(frame[3] == 1U);
  assert(ReadU16Le(&frame[4]) == 0x0007U);
  assert(ReadU16Le(&frame[6]) == 1475U);
  assert(ReadU16Le(&frame[8]) == 1525U);
  assert(ReadU16Le(&frame[10]) == 17U);
  assert(ReadU32Le(&frame[12]) == 0x12345678U);
  assert(ReadU16Le(&frame[16]) == GimbalProtocol_Crc16(frame, 16U));
  assert(memcmp(frame, expected, sizeof(expected)) == 0);
}

static void TestEncodesUnknownAgeAndSaturation(void)
{
  const GimbalTelemetry telemetry = {
      0U,
      GIMBAL_TELEMETRY_STATUS_YAW_SATURATED |
          GIMBAL_TELEMETRY_STATUS_PITCH_SATURATED,
      1000U,
      2000U,
      GIMBAL_TELEMETRY_COMMAND_AGE_UNKNOWN,
      UINT32_MAX};
  uint8_t frame[GIMBAL_TELEMETRY_FRAME_SIZE];

  assert(GimbalTelemetry_Encode(&telemetry, frame));
  assert(ReadU16Le(&frame[4]) == 0x0018U);
  assert(ReadU16Le(&frame[10]) == UINT16_MAX);
  assert(ReadU32Le(&frame[12]) == UINT32_MAX);
}

static void TestRejectsInvalidArguments(void)
{
  GimbalTelemetry telemetry = {0};
  uint8_t frame[GIMBAL_TELEMETRY_FRAME_SIZE];

  assert(!GimbalTelemetry_Encode(NULL, frame));
  assert(!GimbalTelemetry_Encode(&telemetry, NULL));
  telemetry.mode = 3U;
  assert(!GimbalTelemetry_Encode(&telemetry, frame));
}

int main(void)
{
  TestEncodesDocumentedLayout();
  TestEncodesUnknownAgeAndSaturation();
  TestRejectsInvalidArguments();
  puts("gimbal telemetry tests passed");
  return 0;
}
