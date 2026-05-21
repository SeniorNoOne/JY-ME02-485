/*
 * JYME02-485  --  Modbus RTU master driver
 * Target:    Blue Pill  (STM32F103C8T6)
 * Toolchain:   Keil MDK  (CMSIS, direct register access)
 * USART:     USART1   PA9  = TX,  PA10 = RX
 * RS-485:    DE/RE    PA8  (tie together on the transceiver)
 *
 * Wiring  diagram (MAX485 module)
 * Blue Pill PA9  --> DI
 * Blue Pill PA10 <-- RO
 * Blue Pill PA8  --> DE + RE (both pins bridged/soldered)
 * A / B          --> sensor A / B
 * 5 V            --> VCC  (sensor uses 5 V)
 * GND            --> GND
 */

#include "stm32f10x.h"
#include <stdint.h>

// RS-485 direction-control pin
#define DE_RE_PIN     (1u << 8)                 	// PA8
#define DE_RE_HIGH()  (GPIOA->BSRR = DE_RE_PIN)   	// TX enable
#define DE_RE_LOW()   (GPIOA->BRR  = DE_RE_PIN)   	// RX enable

// JY-ME02-485 redister map
#define JYME_SLAVE_ADDR			0x50u    				// default Modbus address 
#define JYME_BAUD				9600u    				// default baud rate 
#define REG_ANGLE				0x11u	   				// Angle reg
#define REG_ROT					0x12u	   				// Number of revolutions
#define REG_ANGLE_ACC			0x13u	   				// Angle acceleration reg
#define REG_TEMP				0x14u	   				// Temp in 0.01 degC
#define MAX_COUNT				0x7FFF					// Max number for 15-bit reg

// MODBUS settings
#define MODBUS_FC_READ_INPUT_REGS  	0x03u
#define RX_BUF_SIZE   				16u
#define TX_TIMEOUT    				50000u

// function declaration
static void clock_init (void);
static void gpio_init (void);
static void usart1_init (void);
static void delay_ms (uint32_t ms);

static void uart_send_byte (uint8_t b);
static int uart_recv_byte (uint8_t *b, uint32_t timeout);

static uint16_t crc16_modbus (const uint8_t *buf, uint16_t len);
static int modbus_read  (uint8_t  slave, 
						 uint8_t  fc, 
						 uint16_t reg_addr,
                         uint16_t num_regs,
                         uint16_t *out);

static double read_angle(void);
static int16_t read_rot(void);
static double read_temp(void);

int main(void)
{
    clock_init();
    gpio_init();
    usart1_init();

    while (1)
    {
        double angle = read_angle();
				int16_t rot = read_rot();
				double temp_C = read_temp();
				
				(void) angle;
				(void) rot;
				(void) temp_C;
			
        delay_ms(1000);
    }
}

static void clock_init(void)
{
		// clock_init � 72 MHz from 8 MHz 
    FLASH->ACR = FLASH_ACR_LATENCY_2 | FLASH_ACR_PRFTBE;

    RCC->CR |= RCC_CR_HSEON;
    while (!(RCC->CR & RCC_CR_HSERDY));

    /* PLL: HSE � 9 = 72 MHz, APB1 = 36 MHz */
    RCC->CFGR = RCC_CFGR_PLLSRC | RCC_CFGR_PLLMULL9 | RCC_CFGR_PPRE1_DIV2;

    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));

    RCC->CFGR |= RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

    SystemCoreClock = 72000000u;
}

static void gpio_init(void)
{
	// PA8  output push-pull 50 MHz  			(DE/RE)
	// PA9  output AF  push-pull 50 MHz  	(USART1 TX)
	// PA10 input  floating             	(USART1 RX)
	RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;

    // CRH  = PA8..PA15   (4 bits each: CNF[1:0] | MODE[1:0])
    GPIOA->CRH = (GPIOA->CRH
					& ~( (0xFu << 0)	// PA8  
					| (0xFu << 4)		// PA9 
					| (0xFu << 8)))		// PA10
					| (0x3u << 0)		// PA8  GP  out PP 50 MHz
					| (0xBu << 4)		// PA9  AF  out PP 50 MHz
					| (0x4u << 8);		// PA10 input floating   

    DE_RE_LOW();		// start in RX mode
}

static void usart1_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_USART1EN;

    USART1->CR1 = 0;
    USART1->CR2 = 0;
    USART1->CR3 = 0;
    USART1->BRR = 7500u;
    USART1->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

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

static void uart_send_byte(uint8_t b)
{
    while (!(USART1->SR & USART_SR_TXE));
    USART1->DR = b;
}

static int uart_recv_byte(uint8_t *b, uint32_t timeout)
{
    while (!(USART1->SR & USART_SR_RXNE))
        if (timeout-- == 0) return -1;
    *b = (uint8_t)(USART1->DR & 0xFFu);
    return 0;
}

static uint16_t crc16_modbus(const uint8_t *buf, uint16_t len)
{
    uint16_t crc = 0xFFFFu;
    for (uint16_t i = 0; i < len; i++)
    {
        crc ^= buf[i];
        for (uint8_t b = 0; b < 8; b++)
            crc = (crc & 1u) ? ((crc >> 1) ^ 0xA001u) : (crc >> 1);
    }
    return crc;
}

static int modbus_read(uint8_t  slave,
                       uint8_t  fc,
                       uint16_t reg_addr,
                       uint16_t num_regs,
                       uint16_t *out)
{
    // Build 8-byte Modbus RTU request
    uint8_t  req[8];
    req[0] = slave;
    req[1] = fc;
    req[2] = (uint8_t)(reg_addr >> 8);
    req[3] = (uint8_t)(reg_addr & 0xFFu);
    req[4] = (uint8_t)(num_regs >> 8);
    req[5] = (uint8_t)(num_regs & 0xFFu);
    uint16_t crc = crc16_modbus(req, 6);
    req[6] = (uint8_t)(crc & 0xFFu);			// low byte first in MODBUS CRC
    req[7] = (uint8_t)(crc >> 8);

    // Transmit
	USART1->SR &= ~USART_SR_TC;   				// clear stale TC flag first
    DE_RE_HIGH();
    for (uint8_t i = 0; i < 8; i++) uart_send_byte(req[i]);
    while (!(USART1->SR & USART_SR_TC));   		// wait until shift-reg empty
    DE_RE_LOW();

    // Receive: 3 header + 2*N data + 2 CRC
    uint8_t expected = (uint8_t)(3u + 2u * num_regs + 2u);
    if (expected > RX_BUF_SIZE) return -1;

    uint8_t rx[RX_BUF_SIZE];
    for (uint8_t i = 0; i < expected; i++)
        if (uart_recv_byte(&rx[i], TX_TIMEOUT) != 0) return -1;

    // Validate CRC
    uint16_t rx_crc   = ((uint16_t)rx[expected - 1] << 8) | rx[expected - 2];
    uint16_t calc_crc = crc16_modbus(rx, (uint16_t)(expected - 2u));
    if (rx_crc != calc_crc) return -1;

    // Unpack big-endian register values
    for (uint16_t i = 0; i < num_regs; i++)
        out[i] = ((uint16_t)rx[3u + i * 2u] << 8) | rx[4u + i * 2u];

    return 0;
}

static double read_angle()
{
	uint16_t buff = 0;
	
	if (modbus_read(JYME_SLAVE_ADDR, MODBUS_FC_READ_INPUT_REGS, REG_ANGLE, 1, &buff) == 0)
	{
		return (double) buff * 360.0 / MAX_COUNT;
	}
	return 0.0;
}

static int16_t read_rot()
{
	uint16_t buff = 0;
	
	if (modbus_read(JYME_SLAVE_ADDR, MODBUS_FC_READ_INPUT_REGS, REG_ROT, 1, &buff) == 0)
	{
		return (int16_t) buff;
	}
	return 0;
}

static double read_temp() 
{
	uint16_t buff = 0;
	
	if (modbus_read(JYME_SLAVE_ADDR, MODBUS_FC_READ_INPUT_REGS, REG_TEMP, 1, &buff) == 0)
	{
		return (double) buff / 100.0;
	}
	return 0.0;
}
