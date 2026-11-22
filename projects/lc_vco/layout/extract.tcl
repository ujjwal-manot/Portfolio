# Extracts the lc_vco layout with wire resistance and every parasitic capacitance into lc_vco_pex.spice next to the GDS, for the post-layout runs: run from build/layout.
gds read lc_vco.gds
load lc_vco
cellname rename lc_vco lc_vco_pex
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
ext2spice -o lc_vco_pex.spice
quit -noprompt
