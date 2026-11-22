# Extracts the opamp layout with wire resistance and every parasitic capacitance into opamp_pex.spice next to the GDS, for the post-layout runs: run from build/layout.
gds read opamp.gds
load opamp
cellname rename opamp opamp_pex
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
ext2spice -o opamp_pex.spice
quit -noprompt
