# Extracts every IHP standard cell named in the CELLS environment variable from the PDK's GDS layout, with wire resistance and every parasitic capacitance, into build/pex/<cell>.spice for characterization.
gds read $::env(PDK_ROOT)/$::env(PDK)/libs.ref/sg13g2_stdcell/gds/sg13g2_stdcell.gds
cd ../build/pex
foreach cell $::env(CELLS) {
  load $cell
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
  ext2spice -o $cell.spice
}
quit -noprompt
