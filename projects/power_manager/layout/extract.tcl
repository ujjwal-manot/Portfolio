# Extracts the layout cell named in the CELL environment variable from CELL.gds with wire resistance and every parasitic capacitance into CELL_pex.spice next to the GDS, for the post-layout runs: run from build/layout.
gds read $::env(CELL).gds
load $::env(CELL)
cellname rename $::env(CELL) $::env(CELL)_pex
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
ext2spice -o $::env(CELL)_pex.spice
quit -noprompt
