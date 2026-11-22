// Drives an 8-bit R-2R DAC on Nucleo-H753ZI PF0..PF7, reads back the analog output on PA3 (ADC1_INP15) with DWT-paced timing, and streams static ramp (R) and coherent 1024-sample sine (S) frames over ST-LINK USART3 (PD8/PD9, 115200 8N1).
#include <stdint.h>
#include <libopencm3/cm3/dwt.h>
#include <libopencm3/cm3/scs.h>
#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/usart.h>

#define ADC1_ISR        MMIO32(ADC1_ADC2_BASE + 0x00U)
#define ADC1_CR         MMIO32(ADC1_ADC2_BASE + 0x08U)
#define ADC1_CFGR       MMIO32(ADC1_ADC2_BASE + 0x0CU)
#define ADC1_SMPR2      MMIO32(ADC1_ADC2_BASE + 0x18U)
#define ADC1_PCSEL      MMIO32(ADC1_ADC2_BASE + 0x1CU)
#define ADC1_SQR1       MMIO32(ADC1_ADC2_BASE + 0x30U)
#define ADC1_DR         MMIO32(ADC1_ADC2_BASE + 0x40U)
#define ADC12_CCR       MMIO32(ADC1_ADC2_BASE + 0x308U)

#define ADC_ISR_ADRDY   (1U << 0)
#define ADC_ISR_EOC     (1U << 2)
#define ADC_CR_ADEN     (1U << 0)
#define ADC_CR_ADSTART  (1U << 2)
#define ADC_CR_ADCALLIN (1U << 16)
#define ADC_CR_ADVREGEN (1U << 28)
#define ADC_CR_DEEPPWD  (1U << 29)
#define ADC_CR_ADCAL    (1U << 31)
#define ADC_CH_PA3      15U

#define HSI_HZ          64000000U
#define SAMPLE_CYCLES   6400U
#define SETTLE_CYCLES   3200U
#define RAMP_AVG_SHIFT  4U
#define SINE_N          1024U

static const uint8_t SINE_LUT[SINE_N] = {
    128U, 138U, 148U, 158U, 167U, 177U, 186U, 195U, 203U, 211U, 218U, 225U, 231U, 237U, 242U, 246U,
    249U, 252U, 253U, 254U, 254U, 254U, 252U, 250U, 247U, 243U, 239U, 234U, 228U, 221U, 214U, 206U,
    198U, 189U, 180U, 171U, 161U, 152U, 141U, 131U, 121U, 111U, 101U,  91U,  82U,  72U,  64U,  55U,
     47U,  39U,  32U,  26U,  20U,  15U,  11U,   7U,   4U,   2U,   1U,   1U,   1U,   2U,   4U,   7U,
     10U,  14U,  19U,  25U,  31U,  38U,  46U,  54U,  62U,  71U,  80U,  90U, 100U, 110U, 120U, 130U,
    140U, 150U, 160U, 170U, 179U, 188U, 197U, 205U, 213U, 220U, 227U, 233U, 238U, 243U, 247U, 250U,
    252U, 254U, 254U, 254U, 254U, 252U, 249U, 246U, 242U, 238U, 232U, 226U, 219U, 212U, 204U, 196U,
    187U, 178U, 169U, 159U, 149U, 139U, 129U, 119U, 109U,  99U,  89U,  80U,  70U,  62U,  53U,  45U,
     38U,  31U,  25U,  19U,  14U,  10U,   6U,   4U,   2U,   1U,   1U,   1U,   2U,   4U,   7U,  11U,
     15U,  21U,  26U,  33U,  40U,  48U,  56U,  64U,  73U,  83U,  92U, 102U, 112U, 122U, 132U, 142U,
    152U, 162U, 172U, 181U, 190U, 199U, 207U, 215U, 222U, 228U, 234U, 239U, 244U, 247U, 250U, 252U,
    254U, 254U, 254U, 253U, 251U, 249U, 245U, 241U, 236U, 231U, 225U, 218U, 210U, 203U, 194U, 185U,
    176U, 167U, 157U, 147U, 137U, 127U, 117U, 107U,  97U,  87U,  77U,  68U,  60U,  51U,  43U,  36U,
     29U,  23U,  18U,  13U,   9U,   6U,   3U,   2U,   1U,   1U,   1U,   3U,   5U,   8U,  12U,  17U,
     22U,  28U,  34U,  42U,  49U,  58U,  66U,  75U,  85U,  94U, 104U, 114U, 124U, 135U, 145U, 155U,
    164U, 174U, 183U, 192U, 201U, 209U, 216U, 223U, 230U, 235U, 240U, 245U, 248U, 251U, 253U, 254U,
    254U, 254U, 253U, 251U, 248U, 245U, 240U, 235U, 230U, 223U, 216U, 209U, 201U, 192U, 183U, 174U,
    164U, 155U, 145U, 135U, 124U, 114U, 104U,  94U,  85U,  75U,  66U,  58U,  49U,  42U,  34U,  28U,
     22U,  17U,  12U,   8U,   5U,   3U,   1U,   1U,   1U,   2U,   3U,   6U,   9U,  13U,  18U,  23U,
     29U,  36U,  43U,  51U,  60U,  68U,  77U,  87U,  97U, 107U, 117U, 127U, 137U, 147U, 157U, 167U,
    176U, 185U, 194U, 203U, 210U, 218U, 225U, 231U, 236U, 241U, 245U, 249U, 251U, 253U, 254U, 254U,
    254U, 252U, 250U, 247U, 244U, 239U, 234U, 228U, 222U, 215U, 207U, 199U, 190U, 181U, 172U, 162U,
    152U, 142U, 132U, 122U, 112U, 102U,  92U,  83U,  73U,  64U,  56U,  48U,  40U,  33U,  26U,  21U,
     15U,  11U,   7U,   4U,   2U,   1U,   1U,   1U,   2U,   4U,   6U,  10U,  14U,  19U,  25U,  31U,
     38U,  45U,  53U,  62U,  70U,  80U,  89U,  99U, 109U, 119U, 129U, 139U, 149U, 159U, 169U, 178U,
    187U, 196U, 204U, 212U, 219U, 226U, 232U, 238U, 242U, 246U, 249U, 252U, 254U, 254U, 254U, 254U,
    252U, 250U, 247U, 243U, 238U, 233U, 227U, 220U, 213U, 205U, 197U, 188U, 179U, 170U, 160U, 150U,
    140U, 130U, 120U, 110U, 100U,  90U,  80U,  71U,  62U,  54U,  46U,  38U,  31U,  25U,  19U,  14U,
     10U,   7U,   4U,   2U,   1U,   1U,   1U,   2U,   4U,   7U,  11U,  15U,  20U,  26U,  32U,  39U,
     47U,  55U,  64U,  72U,  82U,  91U, 101U, 111U, 121U, 131U, 141U, 152U, 161U, 171U, 180U, 189U,
    198U, 206U, 214U, 221U, 228U, 234U, 239U, 243U, 247U, 250U, 252U, 254U, 254U, 254U, 253U, 252U,
    249U, 246U, 242U, 237U, 231U, 225U, 218U, 211U, 203U, 195U, 186U, 177U, 167U, 158U, 148U, 138U,
    127U, 117U, 107U,  97U,  88U,  78U,  69U,  60U,  52U,  44U,  37U,  30U,  24U,  18U,  13U,   9U,
      6U,   3U,   2U,   1U,   1U,   1U,   3U,   5U,   8U,  12U,  16U,  21U,  27U,  34U,  41U,  49U,
     57U,  66U,  75U,  84U,  94U, 103U, 114U, 124U, 134U, 144U, 154U, 164U, 173U, 183U, 191U, 200U,
    208U, 216U, 223U, 229U, 235U, 240U, 244U, 248U, 251U, 253U, 254U, 254U, 254U, 253U, 251U, 248U,
    245U, 241U, 236U, 230U, 224U, 217U, 209U, 201U, 193U, 184U, 175U, 165U, 155U, 145U, 135U, 125U,
    115U, 105U,  95U,  85U,  76U,  67U,  58U,  50U,  42U,  35U,  28U,  22U,  17U,  12U,   8U,   5U,
      3U,   1U,   1U,   1U,   1U,   3U,   6U,   9U,  13U,  17U,  23U,  29U,  36U,  43U,  51U,  59U,
     68U,  77U,  86U,  96U, 106U, 116U, 126U, 136U, 146U, 156U, 166U, 175U, 185U, 193U, 202U, 210U,
    217U, 224U, 230U, 236U, 241U, 245U, 249U, 251U, 253U, 254U, 254U, 254U, 253U, 251U, 248U, 244U,
    240U, 234U, 229U, 222U, 215U, 207U, 199U, 191U, 182U, 172U, 163U, 153U, 143U, 133U, 123U, 113U,
    103U,  93U,  83U,  74U,  65U,  56U,  48U,  40U,  33U,  27U,  21U,  16U,  11U,   8U,   5U,   3U,
      1U,   1U,   1U,   2U,   4U,   6U,  10U,  14U,  19U,  24U,  30U,  37U,  45U,  52U,  61U,  70U,
     79U,  88U,  98U, 108U, 118U, 128U, 138U, 148U, 158U, 168U, 178U, 187U, 195U, 204U, 212U, 219U,
    226U, 232U, 237U, 242U, 246U, 249U, 252U, 253U, 254U, 254U, 254U, 252U, 250U, 247U, 243U, 238U,
    233U, 227U, 221U, 213U, 206U, 197U, 189U, 180U, 170U, 161U, 151U, 141U, 131U, 120U, 110U, 100U,
     91U,  81U,  72U,  63U,  54U,  46U,  39U,  32U,  25U,  20U,  15U,  10U,   7U,   4U,   2U,   1U,
      0U,   1U,   2U,   4U,   7U,  10U,  15U,  20U,  25U,  32U,  39U,  46U,  54U,  63U,  72U,  81U,
     91U, 100U, 110U, 120U, 131U, 141U, 151U, 161U, 170U, 180U, 189U, 197U, 206U, 213U, 221U, 227U,
    233U, 238U, 243U, 247U, 250U, 252U, 254U, 254U, 254U, 253U, 252U, 249U, 246U, 242U, 237U, 232U,
    226U, 219U, 212U, 204U, 195U, 187U, 178U, 168U, 158U, 148U, 138U, 128U, 118U, 108U,  98U,  88U,
     79U,  70U,  61U,  52U,  45U,  37U,  30U,  24U,  19U,  14U,  10U,   6U,   4U,   2U,   1U,   1U,
      1U,   3U,   5U,   8U,  11U,  16U,  21U,  27U,  33U,  40U,  48U,  56U,  65U,  74U,  83U,  93U,
    103U, 113U, 123U, 133U, 143U, 153U, 163U, 172U, 182U, 191U, 199U, 207U, 215U, 222U, 229U, 234U,
    240U, 244U, 248U, 251U, 253U, 254U, 254U, 254U, 253U, 251U, 249U, 245U, 241U, 236U, 230U, 224U,
    217U, 210U, 202U, 193U, 185U, 175U, 166U, 156U, 146U, 136U, 126U, 116U, 106U,  96U,  86U,  77U,
     68U,  59U,  51U,  43U,  36U,  29U,  23U,  17U,  13U,   9U,   6U,   3U,   1U,   1U,   1U,   1U,
      3U,   5U,   8U,  12U,  17U,  22U,  28U,  35U,  42U,  50U,  58U,  67U,  76U,  85U,  95U, 105U,
    115U, 125U, 135U, 145U, 155U, 165U, 175U, 184U, 193U, 201U, 209U, 217U, 224U, 230U, 236U, 241U,
    245U, 248U, 251U, 253U, 254U, 254U, 254U, 253U, 251U, 248U, 244U, 240U, 235U, 229U, 223U, 216U,
    208U, 200U, 191U, 183U, 173U, 164U, 154U, 144U, 134U, 124U, 114U, 103U,  94U,  84U,  75U,  66U,
     57U,  49U,  41U,  34U,  27U,  21U,  16U,  12U,   8U,   5U,   3U,   1U,   1U,   1U,   2U,   3U,
      6U,   9U,  13U,  18U,  24U,  30U,  37U,  44U,  52U,  60U,  69U,  78U,  88U,  97U, 107U, 117U,
};

static uint16_t sine_adc_buf[SINE_N];

static void delay_cycles(uint32_t cycles) {
    uint32_t start = dwt_read_cycle_counter();
    while ((uint32_t)(dwt_read_cycle_counter() - start) < cycles) {
    }
}

static void uart_puts(const char *s) {
    while (*s != '\0') {
        usart_send_blocking(USART3, (uint16_t)(uint8_t)(*s));
        s++;
    }
}

static void uart_put_u32(uint32_t val) {
    char buf[10];
    uint32_t idx = 0U;
    if (val == 0U) {
        usart_send_blocking(USART3, (uint16_t)'0');
        return;
    }
    while (val > 0U && idx < 10U) {
        buf[idx++] = (char)('0' + (val % 10U));
        val /= 10U;
    }
    while (idx > 0U) {
        idx--;
        usart_send_blocking(USART3, (uint16_t)(uint8_t)buf[idx]);
    }
}

static void peripherals_init(void) {
    SCS_DEMCR |= SCS_DEMCR_TRCENA;
    DWT_LAR = 0xC5ACCE55U;
    dwt_enable_cycle_counter();
    rcc_periph_clock_enable(RCC_GPIOA);
    rcc_periph_clock_enable(RCC_GPIOD);
    rcc_periph_clock_enable(RCC_GPIOF);
    rcc_periph_clock_enable(RCC_USART3);
    rcc_periph_clock_enable(RCC_ADC12);

    gpio_mode_setup(GPIOF, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, 0x00FFU);
    gpio_set_output_options(GPIOF, GPIO_OTYPE_PP, GPIO_OSPEED_50MHZ, 0x00FFU);
    gpio_port_write(GPIOF, 0U);

    gpio_mode_setup(GPIOA, GPIO_MODE_ANALOG, GPIO_PUPD_NONE, GPIO3);

    gpio_mode_setup(GPIOD, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO8 | GPIO9);
    gpio_set_af(GPIOD, GPIO_AF7, GPIO8 | GPIO9);
    usart_set_baudrate(USART3, 115200U);
    usart_set_databits(USART3, 8U);
    usart_set_stopbits(USART3, USART_STOPBITS_1);
    usart_set_parity(USART3, USART_PARITY_NONE);
    usart_set_flow_control(USART3, USART_FLOWCONTROL_NONE);
    usart_set_mode(USART3, USART_MODE_TX_RX);
    usart_enable(USART3);

    ADC12_CCR = (3U << 16);
    ADC1_CR &= ~ADC_CR_DEEPPWD;
    ADC1_CR |= ADC_CR_ADVREGEN;
    delay_cycles(HSI_HZ / 10000U);
    ADC1_CR |= ADC_CR_ADCALLIN;
    ADC1_CR |= ADC_CR_ADCAL;
    while ((ADC1_CR & ADC_CR_ADCAL) != 0U) {
    }
    ADC1_CFGR = 0U;
    ADC1_SMPR2 = (5U << 15);
    ADC1_PCSEL = (1U << ADC_CH_PA3);
    ADC1_SQR1 = (ADC_CH_PA3 << 6);
    ADC1_ISR = ADC_ISR_ADRDY;
    ADC1_CR |= ADC_CR_ADEN;
    while ((ADC1_ISR & ADC_ISR_ADRDY) == 0U) {
    }
}

static uint16_t adc1_read_once(void) {
    ADC1_CR |= ADC_CR_ADSTART;
    while ((ADC1_ISR & ADC_ISR_EOC) == 0U) {
    }
    return (uint16_t)(ADC1_DR & 0xFFFFU);
}

static void run_ramp(void) {
    uint32_t code;
    for (code = 0U; code < 256U; code++) {
        uint32_t acc = 0U;
        uint32_t k;
        gpio_port_write(GPIOF, (uint16_t)code);
        delay_cycles(SAMPLE_CYCLES);
        for (k = 0U; k < (1U << RAMP_AVG_SHIFT); k++) {
            acc += (uint32_t)adc1_read_once();
        }
        uart_puts("R ");
        uart_put_u32(code);
        uart_puts(" ");
        uart_put_u32(acc >> RAMP_AVG_SHIFT);
        uart_puts("\r\n");
    }
}

static void run_sine(void) {
    uint32_t i;
    uint32_t t0 = dwt_read_cycle_counter();
    for (i = 0U; i < SINE_N; i++) {
        uint32_t target = t0 + (i * SAMPLE_CYCLES);
        while ((int32_t)(dwt_read_cycle_counter() - target) < 0) {
        }
        gpio_port_write(GPIOF, (uint16_t)SINE_LUT[i]);
        delay_cycles(SETTLE_CYCLES);
        sine_adc_buf[i] = adc1_read_once();
    }
    for (i = 0U; i < SINE_N; i++) {
        uart_puts("S ");
        uart_put_u32(i);
        uart_puts(" ");
        uart_put_u32((uint32_t)SINE_LUT[i]);
        uart_puts(" ");
        uart_put_u32((uint32_t)sine_adc_buf[i]);
        uart_puts("\r\n");
    }
}

int main(void) {
    peripherals_init();
    uart_puts("EDGESENSE_STM32_DAC_READY\r\n");
    run_ramp();
    run_sine();
    for (;;) {
        uint16_t cmd = usart_recv_blocking(USART3);
        if (cmd == (uint16_t)'R') {
            run_ramp();
        } else if (cmd == (uint16_t)'S') {
            run_sine();
        }
    }
}
