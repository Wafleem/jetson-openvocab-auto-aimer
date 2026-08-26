#include "rif.h"

#include "gpdma.h"

void SystemIsolation_Config(void)
{
  RISAF_BaseRegionConfig_t region = {0};
  RIMC_MasterConfig_t otg_master = {0};
  const uint32_t nonsecure = RIF_ATTRIBUTE_NSEC | RIF_ATTRIBUTE_NPRIV;
  const uint32_t dma_nonsecure = DMA_CHANNEL_NSEC | DMA_CHANNEL_NPRIV |
                                 DMA_CHANNEL_SRC_NSEC | DMA_CHANNEL_DEST_NSEC;

  __HAL_RCC_RISAF_CLK_ENABLE();

  region.StartAddress = 0U;
  region.Filtering = RISAF_FILTER_ENABLE;
  region.PrivWhitelist = 0U;
  region.ReadWhitelist = RIF_CID_MASK;
  region.WriteWhitelist = RIF_CID_MASK;

  region.Secure = RIF_ATTRIBUTE_SEC;
  region.EndAddress = 0x00063FFFU;
  HAL_RIF_RISAF_ConfigBaseRegion(RISAF7, RISAF_REGION_1, &region);

  region.EndAddress = 0x000FFFFFU;
  HAL_RIF_RISAF_ConfigBaseRegion(RISAF2, RISAF_REGION_1, &region);

  region.Secure = RIF_ATTRIBUTE_NSEC;
  HAL_RIF_RISAF_ConfigBaseRegion(RISAF3, RISAF_REGION_1, &region);

  if ((HAL_DMA_ConfigChannelAttributes(&handle_GPDMA1_Channel0, dma_nonsecure) != HAL_OK) ||
      (HAL_DMA_ConfigChannelAttributes(&handle_GPDMA1_Channel1, dma_nonsecure) != HAL_OK))
  {
    Error_Handler();
  }

  __HAL_RCC_RIFSC_CLK_ENABLE();

  otg_master.MasterCID = RIF_CID_0;
  otg_master.SecPriv = nonsecure;
  HAL_RIF_RIMC_ConfigMasterAttributes(RIF_MASTER_INDEX_OTG1, &otg_master);

  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RCC_PERIPH_INDEX_GPDMA1, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RCC_PERIPH_INDEX_GPIOA, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RCC_PERIPH_INDEX_GPIOG, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_SYSCFG, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_TIM6, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_TIM14, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_TIM16, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_OTG1HS, nonsecure);
  HAL_RIF_RISC_SetSlaveSecureAttributes(RIF_RISC_PERIPH_INDEX_UCPD1, nonsecure);

  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();
  HAL_GPIO_ConfigPinAttributes(GPIOA, GPIO_PIN_3, GPIO_PIN_NSEC | GPIO_PIN_NPRIV);
  HAL_GPIO_ConfigPinAttributes(GPIOG, GPIO_PIN_2 | GPIO_PIN_8 | GPIO_PIN_10,
                               GPIO_PIN_NSEC | GPIO_PIN_NPRIV);
}
