/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    usbpd.c
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

#include "usbpd.h"

unsigned int USBPD_PreInitOs(void)
{
  if (USBPD_DPM_InitCore() != USBPD_OK)
  {
    return USBPD_ERROR;
  }

  return USBPD_OK;
}

unsigned int MX_USBPD_Init(void)
{
  if (USBPD_DPM_InitOS() != USBPD_OK)
  {
    return USBPD_ERROR;
  }

  return USBPD_OK;
}
