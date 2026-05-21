/*
 * JYME02-485 Modbus RTU master driver
 * Target: 			Blue Pill  (STM32F103C8T6)
 * Toolchain:   Keil MDK   (CMSIS, direct register access)
 * USART: 			USART1   	 PA9  = TX,  PA10 = RX
 * RS-485: 			DE/RE    	 PA8  (tie together on the transceiver side)
 *
 * Wiring  diagram (MAX485 module)
 * Blue Pill PA9  --> DI
 * Blue Pill PA10 <-- RO
 * Blue Pill PA8  --> DE + RE (both pins bridged/soldered)
 * A / B          --> sensor A / B
 * 5 V          	--> VCC  (sensor uses 5 V)
 * GND            --> GND
 */

#include "stm32f10x.h"
#include <stdint.h>

// RS-485 direction-control pin
#define DE_RE_PIN     (1u << 8)               		// PA8
#define DE_RE_HIGH()  (GPIOA->BSRR = DE_RE_PIN)   // TX enable
#define DE_RE_LOW()   (GPIOA->BRR  = DE_RE_PIN)   // RX enable

// JY-ME02-485 redister map
#define JYME_SLAVE_ADDR   0x50u   	// default Modbus address 
#define JYME_BAUD         9600u   	// default baud rate 
#define REG_TEMPERATURE   0x14u 		// Input register: temp  (×0.1 °C)  

// MODBUS settings
#define MODBUS_FC_READ_INPUT_REGS  0x04u
#define RX_BUF_SIZE   16u
#define TX_TIMEOUT    50000u

// function declaration
static void clock_init  (void);
static void gpio_init   (void);
static void usart1_init (void);
static void delay_ms    (uint32_t ms);

// static void uart_send_byte (uint8_t b);
// static int uart_recv_byte (uint8_t *b, uint32_t timeout);

// static uint16_t crc16_modbus (const uint8_t *buf, uint16_t len);
/* static int modbus_read  (uint8_t  slave, 
												 uint8_t  fc, 
												 uint16_t reg_addr,
                         uint16_t num_regs,
                         uint16_t *out);
*/

int main(void)
{
    clock_init();
    gpio_init();
    usart1_init();

    while (1)
    {
        delay_ms(1000);
    }
}

//  clock_init – 72 MHz from 8 MHz 
static void clock_init(void)
{
    FLASH->ACR = FLASH_ACR_LATENCY_2 | FLASH_ACR_PRFTBE;

    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));

    /* PLL: HSE × 9 = 72 MHz, APB1 = 36 MHz */
    RCC->CFGR = RCC_CFGR_PLLSRC | RCC_CFGR_PLLMULL9 | RCC_CFGR_PPRE1_DIV2;

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));

    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

    SystemCoreClock = 72000000u;
}

/*  gpio_init
 *    PA8  output push-pull 50 MHz  (DE/RE)
 *    PA9  output AF  push-pull 50 MHz  (USART1 TX)
 *    PA10 input  floating             (USART1 RX)
 *    PA13 output push-pull  2 MHz     (on-board LED, active-low)
 */
static void gpio_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;

    /* CRH  = PA8..PA15   (4 bits each: CNF[1:0] | MODE[1:0]) */
    GPIOA->CRH = (GPIOA->CRH
        & ~( (0xFu << 0)     /* PA8  */
           | (0xFu << 4)     /* PA9  */
           | (0xFu << 8)     /* PA10 */
           | (0xFu << 20) )) /* PA13 */
        | (0x3u << 0)        /* PA8  GP  out PP 50 MHz */
        | (0xBu << 4)        /* PA9  AF  out PP 50 MHz */
        | (0x4u << 8)        /* PA10 input floating    */
        | (0x2u << 20);      /* PA13 GP  out PP  2 MHz */

    DE_RE_LOW();                          /* start in RX mode          */
    GPIOA->ODR |= (1u << 13);            /* LED off (active-low)       */
}

//  usart1_init – 9600 8N1
//  APB2 = 72 MHz  ?  BRR = 72 000 000 / 9600 = 7500
static void usart1_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    USART1->CR1 = 0;
    USART1->CR2 = 0;
    USART1->CR3 = 0;
    USART1->BRR = 7500u;
    USART1->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

//  delay_ms  –  DWT cycle-counter busy-wait
static void delay_ms(uint32_t ms)
{
    if (!(CoreDebug->DEMCR & CoreDebug_DEMCR_TRCENA_Msk))
    {
        CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        DWT->CYCCNT = 0;
        DWT->CTRL  |= DWT_CTRL_CYCCNTENA_Msk;
    }
    uint32_t ticks = SystemCoreClock / 1000u;
    uint32_t start = DWT->CYCCNT;
    while ((DWT->CYCCNT - start) < ms * ticks);
}

