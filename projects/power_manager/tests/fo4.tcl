# Reports the same fanout-of-4 stage delays as tests/speed.cir from the IHP liberty at the corner in CORNER (slow 1.08 V 125 C, typ 1.20 V 25 C, fast 1.32 V -40 C), averaged over the rising and falling edge across stages 3 and 4, so the transistor sweep can be checked against the characterized library.
set corner $env(CORNER)
set lib [dict get {slow slow_1p08V_125C typ typ_1p20V_25C fast fast_1p32V_m40C} $corner]
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_$lib.lib
read_verilog fo4.v
link_design fo4
set_input_transition 0.02 [get_ports a]
proc arrival {to edge} {
  return [get_property [lindex [get_property [lindex [find_timing_paths -unconstrained -from [get_ports a] -${edge}_to [get_ports $to]] 0] points] end] arrival]
}
set out "$corner"
foreach c {inv nand nor} {
  set d [expr {([arrival ${c}4 rise] - [arrival ${c}2 rise] + [arrival ${c}4 fall] - [arrival ${c}2 fall]) / 4}]
  append out " ${c}_s [format %.4e [expr {$d * 1e-9}]]"
}
puts $out
