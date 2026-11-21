/* Lays out a test built on the standard riscv-tests environment: code from BASE (0 unless given), data after it, and the tohost word at TOHOST when given (the cpu board's result address, left out of the binary), else after the data, where Spike looks for it. */
ENTRY(_start)
SECTIONS {
  . = DEFINED(BASE) ? BASE : 0;
  .text.init : { *(.text.init) }
  .text : { *(.text*) }
  .data : { *(.data*) *(.sdata*) *(.rodata*) *(.bss*) *(.sbss*) }
  .tohost (DEFINED(TOHOST) ? TOHOST : .) (NOLOAD) : { *(.tohost) }
}
