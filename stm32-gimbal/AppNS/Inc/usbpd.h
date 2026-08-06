/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    usbpd.h
  * @author  MCD Application Team
  * @brief   USB Type-C device policy manager initialization.
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */

#ifndef __USBPD_H
#define __USBPD_H

#ifdef __cplusplus
extern "C" {
#endif

#include "usbpd_core.h"
#include "usbpd_dpm_core.h"
#include "usbpd_dpm_conf.h"
#include "usbpd_hw_if.h"

unsigned int USBPD_PreInitOs(void);
unsigned int MX_USBPD_Init(void);

#ifdef __cplusplus
}
#endif

#endif /* __USBPD_H */
