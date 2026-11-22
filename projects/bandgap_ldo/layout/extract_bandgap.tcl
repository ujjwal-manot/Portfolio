# Extracts the bandgap layout with wire resistance and every parasitic capacitance into bandgap_pex.spice next to the GDS, for the post-layout runs: run from build/layout.
gds read bandgap.gds
load bandgap
cellname rename bandgap bandgap_pex
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
ext2spice -o bandgap_pex.spice
quit -noprompt
