#ifndef GIMBAL_PROTOCOL_H
#define GIMBAL_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#include "gimbal_messages.h"

#define GIMBAL_COMMAND_FRAME_SIZE 29U
#define GIMBAL_COMMAND_CRC_OFFSET 27U

typedef struct
{
  uint8_t bytes[GIMBAL_COMMAND_FRAME_SIZE];
  size_t length;
} GimbalProtocolParser;

typedef void (*GimbalCommandHandler)(const GimbalCommand *command, void *context);

void GimbalProtocol_Init(GimbalProtocolParser *parser);
size_t GimbalProtocol_Feed(GimbalProtocolParser *parser,
                           const uint8_t *data,
                           size_t length,
                           GimbalCommandHandler handler,
                           void *context);
uint16_t GimbalProtocol_Crc16(const uint8_t *data, size_t length);

#endif /* GIMBAL_PROTOCOL_H */
