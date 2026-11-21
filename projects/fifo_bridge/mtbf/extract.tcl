# Extracts the IHP sg13g2_dfrbpq_1 flop from its GDS layout with wire resistance and every parasitic capacitance, for the metastability simulation.
gds read $::env(PDK_ROOT)/$::env(PDK)/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds
load sg13g2_dfrbpq_1
cellname rename sg13g2_dfrbpq_1 dfrbpq_pex
cd ../build/mtbf
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
ext2spice -o dfrbpq_pex.spice
quit -noprompt
