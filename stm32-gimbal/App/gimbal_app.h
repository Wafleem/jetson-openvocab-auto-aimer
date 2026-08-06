#ifndef GIMBAL_APP_H
#define GIMBAL_APP_H

#include "ux_api.h"
#include "ux_device_class_cdc_acm.h"

void GimbalApp_Init(void);
void GimbalUsb_SetInstance(UX_SLAVE_CLASS_CDC_ACM *instance);
void GimbalUsbTask(void *argument);
void GimbalControlTask(void *argument);

#endif /* GIMBAL_APP_H */
