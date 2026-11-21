// Reads ADC codes from the stream, undoes the opamp's inversion, runs an 8-tap FIR and a threshold, and times every 64-sample frame.
#define STREAM (*(volatile unsigned *)0x10000000)
#define CYCLES (*(volatile unsigned *)0x10000010)
#define FRAMES 4
#define LEVEL 160

unsigned char out[64 * FRAMES];
unsigned events[FRAMES], frame_cycles[FRAMES];

int main(void) {
    unsigned h0 = 0, h1 = 0, h2 = 0, h3 = 0, h4 = 0, h5 = 0, h6 = 0, h7 = 0;
    unsigned char *y_out = out;
    for (int f = 0; f < FRAMES; f++) {
        unsigned start = CYCLES, count = 0, w;
        do {
            while (!((w = STREAM) >> 31));
            h7 = h6; h6 = h5; h5 = h4; h4 = h3; h3 = h2; h2 = h1; h1 = h0;
            h0 = (w & 0xFF) ^ 0xFF;
            unsigned s3 = h1 + h6, s5 = h2 + h5, s7 = h3 + h4;
            unsigned y = (h0 + h7 + s3 + (s3 << 1) + s5 + (s5 << 2) + (s7 << 3) - s7) >> 5;
            *y_out++ = y;
            count += y > LEVEL;
        } while (!(w & 0x100));
        events[f] = count;
        frame_cycles[f] = CYCLES - start;
    }
    return 0;
}
