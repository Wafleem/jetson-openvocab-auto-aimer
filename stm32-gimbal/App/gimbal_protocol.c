#include "gimbal_protocol.h"

#include <math.h>
#include <stdbool.h>
#include <string.h>

#define GIMBAL_HEADER_0 ((uint8_t)'S')
#define GIMBAL_HEADER_1 ((uint8_t)'P')
#define GIMBAL_MAX_ANGULAR_ERROR_RAD 3.15F

static float GimbalProtocol_ReadFloatLe(const uint8_t *bytes)
{
  uint32_t bits = ((uint32_t)bytes[0]) |
                  ((uint32_t)bytes[1] << 8U) |
                  ((uint32_t)bytes[2] << 16U) |
                  ((uint32_t)bytes[3] << 24U);
  float value;

  memcpy(&value, &bits, sizeof(value));
  return value;
}

uint16_t GimbalProtocol_Crc16(const uint8_t *data, size_t length)
{
  uint16_t crc = 0xFFFFU;

  for (size_t index = 0U; index < length; ++index)
  {
    crc ^= data[index];
    for (uint32_t bit = 0U; bit < 8U; ++bit)
    {
      crc = (crc & 1U) != 0U ? (uint16_t)((crc >> 1U) ^ 0x8408U)
                             : (uint16_t)(crc >> 1U);
    }
  }

  return crc;
}

static bool GimbalProtocol_Decode(const uint8_t *frame, GimbalCommand *command)
{
  const uint16_t received_crc = (uint16_t)frame[GIMBAL_COMMAND_CRC_OFFSET] |
                                ((uint16_t)frame[GIMBAL_COMMAND_CRC_OFFSET + 1U] << 8U);

  if ((frame[0] != GIMBAL_HEADER_0) || (frame[1] != GIMBAL_HEADER_1) ||
      (frame[2] > 2U) ||
      (GimbalProtocol_Crc16(frame, GIMBAL_COMMAND_CRC_OFFSET) != received_crc))
  {
    return false;
  }

  command->mode = frame[2];
  command->yaw_error_rad = GimbalProtocol_ReadFloatLe(&frame[3]);
  command->yaw_velocity_rad_s = GimbalProtocol_ReadFloatLe(&frame[7]);
  command->yaw_acceleration_rad_s2 = GimbalProtocol_ReadFloatLe(&frame[11]);
  command->pitch_error_rad = GimbalProtocol_ReadFloatLe(&frame[15]);
  command->pitch_velocity_rad_s = GimbalProtocol_ReadFloatLe(&frame[19]);
  command->pitch_acceleration_rad_s2 = GimbalProtocol_ReadFloatLe(&frame[23]);
  command->received_tick_ms = 0U;

  return isfinite(command->yaw_error_rad) &&
         (fabsf(command->yaw_error_rad) <= GIMBAL_MAX_ANGULAR_ERROR_RAD) &&
         isfinite(command->yaw_velocity_rad_s) &&
         isfinite(command->yaw_acceleration_rad_s2) &&
         isfinite(command->pitch_error_rad) &&
         (fabsf(command->pitch_error_rad) <= GIMBAL_MAX_ANGULAR_ERROR_RAD) &&
         isfinite(command->pitch_velocity_rad_s) &&
         isfinite(command->pitch_acceleration_rad_s2);
}

static void GimbalProtocol_Resynchronize(GimbalProtocolParser *parser)
{
  for (size_t start = 1U; start + 1U < parser->length; ++start)
  {
    if ((parser->bytes[start] == GIMBAL_HEADER_0) &&
        (parser->bytes[start + 1U] == GIMBAL_HEADER_1))
    {
      parser->length -= start;
      memmove(parser->bytes, &parser->bytes[start], parser->length);
      return;
    }
  }

  if ((parser->length > 0U) && (parser->bytes[parser->length - 1U] == GIMBAL_HEADER_0))
  {
    parser->bytes[0] = GIMBAL_HEADER_0;
    parser->length = 1U;
  }
  else
  {
    parser->length = 0U;
  }
}

void GimbalProtocol_Init(GimbalProtocolParser *parser)
{
  if (parser != NULL)
  {
    parser->length = 0U;
  }
}

size_t GimbalProtocol_Feed(GimbalProtocolParser *parser,
                           const uint8_t *data,
                           size_t length,
                           GimbalCommandHandler handler,
                           void *context)
{
  size_t decoded_count = 0U;

  if ((parser == NULL) || ((data == NULL) && (length != 0U)))
  {
    return 0U;
  }

  for (size_t index = 0U; index < length; ++index)
  {
    const uint8_t byte = data[index];

    if (parser->length == 0U)
    {
      if (byte == GIMBAL_HEADER_0)
      {
        parser->bytes[0] = byte;
        parser->length = 1U;
      }
      continue;
    }

    if (parser->length == 1U)
    {
      if (byte == GIMBAL_HEADER_1)
      {
        parser->bytes[1] = byte;
        parser->length = 2U;
      }
      else if (byte != GIMBAL_HEADER_0)
      {
        parser->length = 0U;
      }
      continue;
    }

    parser->bytes[parser->length++] = byte;
    if (parser->length == GIMBAL_COMMAND_FRAME_SIZE)
    {
      GimbalCommand command;

      if (GimbalProtocol_Decode(parser->bytes, &command))
      {
        if (handler != NULL)
        {
          handler(&command, context);
        }
        ++decoded_count;
        parser->length = 0U;
      }
      else
      {
        GimbalProtocol_Resynchronize(parser);
      }
    }
  }

  return decoded_count;
}
