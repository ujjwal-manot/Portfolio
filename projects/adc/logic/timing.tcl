# Checks sar_logic timing at the corner named by CORNER (slow 1.08 V 125 C, typ 1.2 V 25 C, fast 1.32 V -40 C) on the mapped netlist with a 10 MHz clk: comp_out comes from the comparator, which is clocked by comp_clk at the falling clk edge and latches within 3 ns (slowest decision in results/decide.log is under 1 ns), so it arrives 53 ns into the cycle; dac, cal, trim and samp switch the DAC and must settle before the comparator fires 50 ns into the cycle, so they must arrive within 20 ns (30 ns left for the switches and the plate); comp_clk is the gated clock itself; the m_ outputs go to fifo_bridge's s_clk flops with 20 ns of the cycle as an interface budget, like its own timing.tcl; inputs driven by an IHP flop and outputs loading one IHP flop D pin; rst_n is untimed (released by the reset synchronizer upstream); at the slow corner late cell delays and setup checks are raised 1.6%, since at 1.08 V the cold slow corner (ss, -40 C, which IHP ships no library for) is that much slower than the 125 C library in power_manager's transistor sweep (projects/power_manager/results/speed.log, vdd 1.08 V); writes m_tvalid's clock-to-output delay before that derate (the timed gate run uses the underated SDF and must match it), then the corner's SDF.
set corner $::env(CORNER)
read_liberty ../build/$corner.lib
read_verilog ../build/sar_logic_cells.v
link_design sar_logic
create_clock -name clk -period 100 [get_ports clk]
set_input_delay 0 -clock clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 53 -clock clk [get_ports comp_out]
set_input_delay 20 -clock clk [get_ports m_tready]
set_output_delay 80 -clock clk [get_ports {dac* cal trim* samp}]
set_output_delay 20 -clock clk [get_ports {m_tvalid m_tdata* m_tlast overflow}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n comp_out m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
set out [open ../build/clock_to_output_$corner.txt w]
set net [get_nets m_tvalid]
while {[get_property [set drive [get_pins -of_objects $net -filter "direction==output"]] lib_pin_name] != "Q"} {
  set net [get_nets -of_objects [get_pins -of_objects [get_cells -of_objects $drive] -filter "lib_pin_name==A"]]
}
set clock [get_pins -of_objects [get_cells -of_objects $drive] -filter "lib_pin_name==CLK"]
set edges {}
foreach edge {rise fall} {
  lappend edges [format %.4f [get_property [lindex [get_property [find_timing_paths -path_delay max -from $clock -${edge}_to [get_ports m_tvalid]] points] end] arrival]]
}
puts $out "m_tvalid $edges"
close $out
puts "clock to output m_tvalid: rise [lindex $edges 0] ns, fall [lindex $edges 1] ns after the clk pin edge"
if {$corner == "slow"} { set_timing_derate -late -cell_delay 1.016; set_timing_derate -late -cell_check 1.016 }
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
write_sdf -no_timestamp -digits 4 ../build/sar_logic_$corner.sdf
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns"
exit [expr {$setup < 0 || $hold < 0}]
