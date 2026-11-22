# OpenSTA 3-corner (slow, typ, fast) timing, cell count, area, and fmax signoff script for compare_with_papers/reference_block/spm.v at 100 MHz (10 ns period) on IHP SG13G2.
set corner $::env(CORNER)
set cells [dict get {slow slow_1p08V_125C typ typ_1p20V_25C fast fast_1p32V_m40C} $corner]
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_$cells.lib
read_verilog build/spm_cells.v
link_design spm
create_clock -name clk -period 10 [get_ports clk]
if {$corner == "slow"} { set_timing_derate -late -cell_delay 1.016; set_timing_derate -late -cell_check 1.016 }
set_input_delay 2 -clock clk [get_ports {x a*}]
set_input_delay 0 -clock clk [get_ports rst]
set_false_path -from [get_ports rst]
set_output_delay 2 -clock clk [get_ports y]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst x a*}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [get_ports y]
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
set min_period [expr {10.0 - $setup}]
set fmax_mhz [expr {1000.0 / $min_period}]
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns, fmax [format %.2f $fmax_mhz] MHz"
exit [expr {$setup < 0 || $hold < 0}]
