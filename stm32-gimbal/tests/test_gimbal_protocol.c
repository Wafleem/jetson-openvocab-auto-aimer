#include <assert.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../App/gimbal_protocol.h"

typedef struct
{
  GimbalCommand commands[8];
  size_t count;
} Capture;

static void WriteFloatLe(uint8_t *destination, float value)
{
  uint32_t bits;

  memcpy(&bits, &value, sizeof(bits));
  destination[0] = (uint8_t)bits;
  destination[1] = (uint8_t)(bits >> 8U);
  destination[2] = (uint8_t)(bits >> 16U);
  destination[3] = (uint8_t)(bits >> 24U);
}

static void BuildFrame(uint8_t frame[GIMBAL_COMMAND_FRAME_SIZE],
                       uint8_t mode,
                       float yaw_error,
                       float pitch_error)
{
  uint16_t crc;

  memset(frame, 0, GIMBAL_COMMAND_FRAME_SIZE);
  frame[0] = (uint8_t)'S';
  frame[1] = (uint8_t)'P';
  frame[2] = mode;
  WriteFloatLe(&frame[3], yaw_error);
  WriteFloatLe(&frame[15], pitch_error);
  crc = GimbalProtocol_Crc16(frame, GIMBAL_COMMAND_CRC_OFFSET);
  frame[27] = (uint8_t)crc;
  frame[28] = (uint8_t)(crc >> 8U);
}

static void CaptureCommand(const GimbalCommand *command, void *context)
{
  Capture *capture = context;

  assert(capture->count < (sizeof(capture->commands) / sizeof(capture->commands[0])));
  capture->commands[capture->count++] = *command;
}

static void TestCrcCheckValue(void)
{
  static const uint8_t digits[] = "123456789";

  assert(GimbalProtocol_Crc16(digits, sizeof(digits) - 1U) == 0x6F91U);
}

static void TestEverySplitPoint(void)
{
  uint8_t frame[GIMBAL_COMMAND_FRAME_SIZE];

  BuildFrame(frame, 1U, -0.25F, 0.125F);
  for (size_t split = 0U; split <= GIMBAL_COMMAND_FRAME_SIZE; ++split)
  {
    GimbalProtocolParser parser;
    Capture capture = {0};

    GimbalProtocol_Init(&parser);
    assert(GimbalProtocol_Feed(&parser, frame, split, CaptureCommand, &capture) ==
           (split == GIMBAL_COMMAND_FRAME_SIZE ? 1U : 0U));
    assert(GimbalProtocol_Feed(&parser,
                               &frame[split],
                               GIMBAL_COMMAND_FRAME_SIZE - split,
                               CaptureCommand,
                               &capture) ==
           (split == GIMBAL_COMMAND_FRAME_SIZE ? 0U : 1U));
    assert(capture.count == 1U);
    assert(capture.commands[0].mode == 1U);
    assert(fabsf(capture.commands[0].yaw_error_rad + 0.25F) < 0.00001F);
    assert(fabsf(capture.commands[0].pitch_error_rad - 0.125F) < 0.00001F);
  }
}

static void TestCoalescedFramesAndGarbage(void)
{
  uint8_t first[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t second[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t stream[3U + GIMBAL_COMMAND_FRAME_SIZE * 2U];
  GimbalProtocolParser parser;
  Capture capture = {0};

  BuildFrame(first, 1U, -0.1F, 0.2F);
  BuildFrame(second, 2U, 0.3F, -0.4F);
  stream[0] = 0x00U;
  stream[1] = (uint8_t)'S';
  stream[2] = 0x7FU;
  memcpy(&stream[3], first, sizeof(first));
  memcpy(&stream[3U + sizeof(first)], second, sizeof(second));

  GimbalProtocol_Init(&parser);
  assert(GimbalProtocol_Feed(&parser,
                             stream,
                             sizeof(stream),
                             CaptureCommand,
                             &capture) == 2U);
  assert(capture.count == 2U);
  assert(capture.commands[0].mode == 1U);
  assert(capture.commands[1].mode == 2U);
}

static void TestBadFramesDoNotPublish(void)
{
  uint8_t bad_crc[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t nonfinite[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t out_of_range[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t valid[GIMBAL_COMMAND_FRAME_SIZE];
  uint8_t stream[GIMBAL_COMMAND_FRAME_SIZE * 4U];
  GimbalProtocolParser parser;
  Capture capture = {0};
  uint16_t crc;

  BuildFrame(bad_crc, 1U, 0.1F, 0.2F);
  bad_crc[8] ^= 0x80U;

  BuildFrame(nonfinite, 1U, 0.1F, 0.2F);
  WriteFloatLe(&nonfinite[3], INFINITY);
  crc = GimbalProtocol_Crc16(nonfinite, GIMBAL_COMMAND_CRC_OFFSET);
  nonfinite[27] = (uint8_t)crc;
  nonfinite[28] = (uint8_t)(crc >> 8U);

  BuildFrame(out_of_range, 1U, 3.2F, 0.0F);

  BuildFrame(valid, 0U, 0.0F, 0.0F);
  memcpy(stream, bad_crc, sizeof(bad_crc));
  memcpy(&stream[sizeof(bad_crc)], nonfinite, sizeof(nonfinite));
  memcpy(&stream[sizeof(bad_crc) + sizeof(nonfinite)], out_of_range, sizeof(out_of_range));
  memcpy(&stream[sizeof(bad_crc) + sizeof(nonfinite) + sizeof(out_of_range)],
         valid,
         sizeof(valid));

  GimbalProtocol_Init(&parser);
  assert(GimbalProtocol_Feed(&parser,
                             stream,
                             sizeof(stream),
                             CaptureCommand,
                             &capture) == 1U);
  assert(capture.count == 1U);
  assert(capture.commands[0].mode == 0U);
}

int main(void)
{
  TestCrcCheckValue();
  TestEverySplitPoint();
  TestCoalescedFramesAndGarbage();
  TestBadFramesDoNotPublish();
  puts("gimbal protocol tests passed");
  return 0;
}
