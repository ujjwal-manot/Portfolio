/* Places code at 0 and data right after it, all inside the 64 KB RAM. */
ENTRY(_start)
SECTIONS {
  . = DEFINED(BASE) ? BASE : 0;
  .text : { *(.text*) }
  .data : { *(.data*) *(.sdata*) *(.rodata*) *(.bss*) *(.sbss*) }
}
