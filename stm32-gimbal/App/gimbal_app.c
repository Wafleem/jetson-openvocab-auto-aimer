#include "gimbal_app.h"

#include <stdbool.h>
#include <stdint.h>

#include "FreeRTOS.h"
#include "task.h"
#include "ux_api.h"

#include "../AppNS/Inc/main.h"
#include "../AppNS/Inc/tim.h"
#include "gimbal_messages.h"
#include "gimbal_protocol.h"

#define GIMBAL_USB_TASK_STACK_WORDS       768U
#define GIMBAL_CONTROL_TASK_STACK_WORDS   384U
#define GIMBAL_CONTROL_PERIOD_MS          20U
#define GIMBAL_COMMAND_TIMEOUT_MS         250U
#define GIMBAL_SERVO_NEUTRAL_US           1500.0F
#define GIMBAL_SERVO_MIN_US               1000.0F
#define GIMBAL_SERVO_MAX_US               2000.0F
#define GIMBAL_SERVO_MAX_RATE_US_S        800.0F
#define GIMBAL_YAW_KP_US_S_PER_RAD        650.0F
#define GIMBAL_YAW_KI_US_S_PER_RAD_S      100.0F
#define GIMBAL_YAW_KD_US_PER_RAD           5.0F
#define GIMBAL_PITCH_KP_US_S_PER_RAD      650.0F
#define GIMBAL_PITCH_KI_US_S_PER_RAD_S    100.0F
#define GIMBAL_PITCH_KD_US_PER_RAD         5.0F
#define GIMBAL_YAW_DIRECTION              1.0F
#define GIMBAL_PITCH_DIRECTION            1.0F

typedef struct
{
  float setpoint_us;
  float integral;
  float previous_error;
  bool previous_valid;
} ServoController;

static StaticTask_t usb_task_control;
static StackType_t usb_task_stack[GIMBAL_USB_TASK_STACK_WORDS];
static StaticTask_t control_task_control;
static StackType_t control_task_stack[GIMBAL_CONTROL_TASK_STACK_WORDS];

static volatile UX_SLAVE_CLASS_CDC_ACM *cdc_acm_instance;
static volatile uint32_t cdc_acm_epoch;

static float GimbalClamp(float value, float minimum, float maximum)
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

static void GimbalControllerHold(ServoController *controller)
{
  controller->integral = 0.0F;
  controller->previous_valid = false;
}

static void GimbalControllerStep(ServoController *controller,
                                 float error_rad,
                                 float kp,
                                 float ki,
                                 float kd,
                                 float direction)
{
  const float period_s = (float)GIMBAL_CONTROL_PERIOD_MS / 1000.0F;
  float derivative_rad_s = 0.0F;
  float rate_us_s;

  controller->integral = GimbalClamp(controller->integral + error_rad * period_s,
                                     -1.0F,
                                     1.0F);
  if (controller->previous_valid)
  {
    derivative_rad_s = (error_rad - controller->previous_error) / period_s;
  }
  controller->previous_error = error_rad;
  controller->previous_valid = true;

  rate_us_s = direction * ((kp * error_rad) +
                           (ki * controller->integral) +
                           (kd * derivative_rad_s));
  rate_us_s = GimbalClamp(rate_us_s,
                          -GIMBAL_SERVO_MAX_RATE_US_S,
                          GIMBAL_SERVO_MAX_RATE_US_S);
  controller->setpoint_us = GimbalClamp(controller->setpoint_us + rate_us_s * period_s,
                                        GIMBAL_SERVO_MIN_US,
                                        GIMBAL_SERVO_MAX_US);
}

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
  uint32_t observed_epoch = cdc_acm_epoch;

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
    }

    vTaskDelay(pdMS_TO_TICKS(1U));
  }
}

void GimbalControlTask(void *argument)
{
  ServoController yaw = {GIMBAL_SERVO_NEUTRAL_US, 0.0F, 0.0F, false};
  ServoController pitch = {GIMBAL_SERVO_NEUTRAL_US, 0.0F, 0.0F, false};
  TickType_t last_wake = xTaskGetTickCount();

  (void)argument;
  __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, (uint32_t)yaw.setpoint_us);
  __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, (uint32_t)pitch.setpoint_us);
  if ((HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_1) != HAL_OK) ||
      (HAL_TIM_PWM_Start(&htim2, TIM_CHANNEL_2) != HAL_OK))
  {
    Error_Handler();
  }

  for (;;)
  {
    GimbalCommand command;
    const bool have_command = GimbalMessages_ReadLatestCommand(&command);
    const bool command_fresh = have_command &&
                               ((uint32_t)(HAL_GetTick() - command.received_tick_ms) <=
                                GIMBAL_COMMAND_TIMEOUT_MS);

    if (command_fresh && (command.mode != 0U))
    {
      GimbalControllerStep(&yaw,
                           command.yaw_error_rad,
                           GIMBAL_YAW_KP_US_S_PER_RAD,
                           GIMBAL_YAW_KI_US_S_PER_RAD_S,
                           GIMBAL_YAW_KD_US_PER_RAD,
                           GIMBAL_YAW_DIRECTION);
      GimbalControllerStep(&pitch,
                           command.pitch_error_rad,
                           GIMBAL_PITCH_KP_US_S_PER_RAD,
                           GIMBAL_PITCH_KI_US_S_PER_RAD_S,
                           GIMBAL_PITCH_KD_US_PER_RAD,
                           GIMBAL_PITCH_DIRECTION);
    }
    else
    {
      GimbalControllerHold(&yaw);
      GimbalControllerHold(&pitch);
    }

    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_1, (uint32_t)yaw.setpoint_us);
    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, (uint32_t)pitch.setpoint_us);
    vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(GIMBAL_CONTROL_PERIOD_MS));
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
