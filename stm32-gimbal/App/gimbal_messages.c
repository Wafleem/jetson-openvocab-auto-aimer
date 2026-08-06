#include "gimbal_messages.h"

#include "FreeRTOS.h"
#include "queue.h"

static StaticQueue_t command_queue_control;
static uint32_t command_queue_storage[(sizeof(GimbalCommand) + sizeof(uint32_t) - 1U) /
                                      sizeof(uint32_t)];
static QueueHandle_t command_queue;

bool GimbalMessages_Init(void)
{
  if (command_queue == NULL)
  {
    command_queue = xQueueCreateStatic(1U,
                                       sizeof(GimbalCommand),
                                       (uint8_t *)command_queue_storage,
                                       &command_queue_control);
  }

  return command_queue != NULL;
}

bool GimbalMessages_PublishCommand(const GimbalCommand *command)
{
  if ((command_queue == NULL) || (command == NULL))
  {
    return false;
  }

  return xQueueOverwrite(command_queue, command) == pdPASS;
}

bool GimbalMessages_ReadLatestCommand(GimbalCommand *command)
{
  if ((command_queue == NULL) || (command == NULL))
  {
    return false;
  }

  return xQueuePeek(command_queue, command, 0U) == pdPASS;
}
