# Checks frac_n_pll mash111 sigma-delta modulator timing across slow (1.08 V, 125 C with 1.6% cold-corner derate), typ (1.20 V, 25 C), and fast (1.32 V, -40 C) IHP SG13G2 corners at the 50 MHz reference clock (20 ns period).
set corner $::env(CORNER)
read_liberty ../build/$corner.lib
read_verilog ../build/mash111_cells.v
link_design mash111
create_clock -name clk -period 20 [get_ports clk]
if {$corner == "slow"} { set_timing_derate -late -cell_delay 1.016; set_timing_derate -late -cell_check 1.016 }
set_input_delay 0 -clock clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 4 -clock clk [get_ports {frac_in*}]
set_output_delay 4 -clock clk [get_ports {dither_out*}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n frac_in*}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
write_sdf -no_timestamp -digits 4 ../build/mash111_$corner.sdf
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns"
exit [expr {$setup < 0 || $hold < 0}]
