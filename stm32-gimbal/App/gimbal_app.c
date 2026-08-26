#include "gimbal_app.h"

#include <stdbool.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "task.h"
#include "ux_api.h"

#include "../AppNS/Inc/main.h"
#include "../AppNS/Inc/tim.h"
#include "gimbal_control.h"
#include "gimbal_messages.h"
#include "gimbal_protocol.h"
#include "gimbal_telemetry.h"

#define GIMBAL_USB_TASK_STACK_WORDS       768U
#define GIMBAL_CONTROL_TASK_STACK_WORDS   384U
#define GIMBAL_COMMAND_TIMEOUT_MS         250U
#define GIMBAL_TELEMETRY_PERIOD_MS        100U

static StaticTask_t usb_task_control;
static StackType_t usb_task_stack[GIMBAL_USB_TASK_STACK_WORDS];
static StaticTask_t control_task_control;
static StackType_t control_task_stack[GIMBAL_CONTROL_TASK_STACK_WORDS];

static volatile UX_SLAVE_CLASS_CDC_ACM *cdc_acm_instance;
static volatile uint32_t cdc_acm_epoch;

static void GimbalPublishDecodedCommand(const GimbalCommand *command, void *context)
{
  GimbalCommand timestamped = *command;

  (void)context;
  timestamped.received_tick_ms = HAL_GetTick();
  (void)GimbalMessages_PublishCommand(&timestamped);
}

void GimbalUsb_SetInstance(UX_SLAVE_CLASS_CDC_ACM *instance)
{
  cdc_acm_instance = instance;
  ++cdc_acm_epoch;
}

void GimbalUsbTask(void *argument)
{
  GimbalProtocolParser parser;
  uint8_t receive_buffer[64];
  uint8_t transmit_buffer[GIMBAL_TELEMETRY_FRAME_SIZE];
  uint32_t observed_epoch = cdc_acm_epoch;
  TickType_t last_telemetry_tick = xTaskGetTickCount();
  bool transmit_pending = false;

  (void)argument;
  GimbalProtocol_Init(&parser);

  for (;;)
  {
    ULONG actual_length = 0U;
    UX_SLAVE_CLASS_CDC_ACM *instance;

    (void)ux_device_stack_tasks_run();

    if (observed_epoch != cdc_acm_epoch)
    {
      observed_epoch = cdc_acm_epoch;
      GimbalProtocol_Init(&parser);
      transmit_pending = false;
    }

    instance = (UX_SLAVE_CLASS_CDC_ACM *)cdc_acm_instance;
    if (instance != UX_NULL)
    {
      const UINT state = ux_device_class_cdc_acm_read_run(instance,
                                                           receive_buffer,
                                                           sizeof(receive_buffer),
                                                           &actual_length);
      if ((state == UX_STATE_NEXT) && (actual_length > 0U))
      {
        (void)GimbalProtocol_Feed(&parser,
                                  receive_buffer,
                                  (size_t)actual_length,
                                  GimbalPublishDecodedCommand,
                                  NULL);
      }

      if (!transmit_pending &&
          ((TickType_t)(xTaskGetTickCount() - last_telemetry_tick) >=
           pdMS_TO_TICKS(GIMBAL_TELEMETRY_PERIOD_MS)))
      {
        GimbalTelemetry telemetry;

        if (GimbalMessages_ReadLatestTelemetry(&telemetry))
        {
          telemetry.status_flags |= GIMBAL_TELEMETRY_STATUS_USB_CONNECTED;
          transmit_pending = GimbalTelemetry_Encode(&telemetry, transmit_buffer);
          last_telemetry_tick = xTaskGetTickCount();
        }
      }

      if (transmit_pending)
      {
        ULONG transmitted_length = 0U;
        const UINT transmit_state = ux_device_class_cdc_acm_write_run(
            instance,
            transmit_buffer,
            sizeof(transmit_buffer),
            &transmitted_length);

        if (transmit_state == UX_STATE_NEXT)
        {
          transmit_pending = false;
        }
        else if (transmit_state < UX_STATE_NEXT)
        {
          transmit_pending = false;
        }
      }
    }

    vTaskDelay(pdMS_TO_TICKS(1U));
  }
}

void GimbalControlTask(void *argument)
{
  GimbalControl control;
  const GimbalControlConfig config = GimbalControl_DefaultConfig();
  GimbalControlOutput output;
  uint32_t telemetry_sequence = 0U;
  TickType_t last_wake = xTaskGetTickCount();

  (void)argument;
  if (!GimbalControl_Init(&control, &config))
  {
    Error_Handler();
  }
  output = GimbalControl_GetOutput(&control);
  __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, output.yaw_pulse_us);
  __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, output.pitch_pulse_us);
  if ((HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1) != HAL_OK) ||
      (HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_2) != HAL_OK))
  {
    Error_Handler();
  }

  for (;;)
  {
    GimbalCommand command;
    GimbalTelemetry telemetry;
    const bool have_command = GimbalMessages_ReadLatestCommand(&command);
    const uint32_t command_age_ms = have_command
                                        ? (uint32_t)(HAL_GetTick() - command.received_tick_ms)
                                        : UINT32_MAX;
    const bool command_fresh = have_command &&
                               (command_age_ms <= GIMBAL_COMMAND_TIMEOUT_MS);

    if (command_fresh && (command.mode != 0U))
    {
      GimbalControl_Step(&control, &command);
    }
    else
    {
      GimbalControl_Hold(&control);
    }

    output = GimbalControl_GetOutput(&control);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, output.yaw_pulse_us);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, output.pitch_pulse_us);

    telemetry.mode = output.mode;
    telemetry.status_flags = 0U;
    if (command_fresh)
    {
      telemetry.status_flags |= GIMBAL_TELEMETRY_STATUS_COMMAND_FRESH;
    }
    if (output.mode != 0U)
    {
      telemetry.status_flags |= GIMBAL_TELEMETRY_STATUS_TRACKING_ACTIVE;
    }
    if (output.yaw_saturated)
    {
      telemetry.status_flags |= GIMBAL_TELEMETRY_STATUS_YAW_SATURATED;
    }
    if (output.pitch_saturated)
    {
      telemetry.status_flags |= GIMBAL_TELEMETRY_STATUS_PITCH_SATURATED;
    }
    telemetry.yaw_pulse_us = output.yaw_pulse_us;
    telemetry.pitch_pulse_us = output.pitch_pulse_us;
    telemetry.command_age_ms = !have_command
                                   ? GIMBAL_TELEMETRY_COMMAND_AGE_UNKNOWN
                                   : (uint16_t)(command_age_ms >= UINT16_MAX
                                                    ? UINT16_MAX - 1U
                                                    : command_age_ms);
    telemetry.sequence = telemetry_sequence++;
    (void)GimbalMessages_PublishTelemetry(&telemetry);

    vTaskDelayUntil(&last_wake,
                    pdMS_TO_TICKS(GIMBAL_CONTROL_DEFAULT_PERIOD_MS));
  }
}

void GimbalApp_Init(void)
{
  TaskHandle_t usb_task;
  TaskHandle_t control_task;

  if (!GimbalMessages_Init())
  {
    Error_Handler();
  }

  usb_task = xTaskCreateStatic(GimbalUsbTask,
                               "gimbal-usb",
                               GIMBAL_USB_TASK_STACK_WORDS,
                               NULL,
                               tskIDLE_PRIORITY + 3U,
                               usb_task_stack,
                               &usb_task_control);
  control_task = xTaskCreateStatic(GimbalControlTask,
                                   "gimbal-control",
                                   GIMBAL_CONTROL_TASK_STACK_WORDS,
                                   NULL,
                                   tskIDLE_PRIORITY + 2U,
                                   control_task_stack,
                                   &control_task_control);
  if ((usb_task == NULL) || (control_task == NULL))
  {
    Error_Handler();
  }
}
