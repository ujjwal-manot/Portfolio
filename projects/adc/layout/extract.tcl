# Extracts the ADC core layout (cap DAC array, switches and comparator) with wire resistance and every parasitic capacitance into adc_core_pex.spice next to the GDS, for the post-layout conversion: run from build/layout.
gds read adc_core.gds
load adc_core
cellname rename adc_core adc_core_pex
extract do resistance
extract all
ext2sim labels on
ext2sim
extresist tolerance 1
extresist all
ext2spice format ngspice
ext2spice cthresh 0
ext2spice extresist on
ext2spice subcircuit top on
ext2spice -o adc_core_pex.spice
quit -noprompt
