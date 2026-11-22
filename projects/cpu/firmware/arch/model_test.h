// riscv-arch-test target macros shared by the cpu board and Spike: the test ends by writing 1 to tohost (the board's result address 0x1000_0100 when linked with TOHOST, else a word after the data where Spike polls), and the signature is the words from begin_signature to end_signature; this cpu has no software or external interrupt lines a test could raise, so those hooks are empty.
#define RVMODEL_DATA_SECTION .pushsection .tohost,"aw",@progbits; .align 8; .global tohost; tohost: .dword 0; .align 8; .global fromhost; fromhost: .dword 0; .popsection;
#define RVMODEL_HALT li x1, 1; 1: sw x1, tohost, t2; j 1b;
#define RVMODEL_BOOT
#define RVMODEL_DATA_BEGIN RVMODEL_DATA_SECTION .align 2; .global begin_signature; begin_signature:
#define RVMODEL_DATA_END .global end_signature; end_signature:
#define RVMODEL_IO_INIT
#define RVMODEL_IO_WRITE_STR(_R, _STR)
#define RVMODEL_IO_CHECK()
#define RVMODEL_IO_ASSERT_GPR_EQ(_S, _R, _I)
#define RVMODEL_IO_ASSERT_SFPR_EQ(_F, _R, _I)
#define RVMODEL_IO_ASSERT_DFPR_EQ(_D, _R, _I)
#define RVMODEL_SET_MSW_INT
#define RVMODEL_CLEAR_MSW_INT
#define RVMODEL_CLEAR_MTIMER_INT
#define RVMODEL_CLEAR_MEXT_INT
