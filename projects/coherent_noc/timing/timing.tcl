# Checks coherent_noc xy_router timing across slow (1.08 V, 125 C with 1.6% cold-corner derate), typ (1.20 V, 25 C), and fast (1.32 V, -40 C) IHP SG13G2 corners at 50 MHz (20 ns period) with sg13g2_dfrbpq_1 drivers and loads.
set corner $::env(CORNER)
set routed [info exists ::env(SPEF)]
read_liberty ../build/$corner.lib
read_verilog [expr {$routed ? $::env(NETLIST) : "../build/xy_router_cells.v"}]
link_design xy_router
if {$routed} { read_spef $::env(SPEF) }
create_clock -name clk -period 20 [get_ports clk]
if {$routed} { set_propagated_clock [all_clocks] }
if {$corner == "slow"} { set_timing_derate -late -cell_delay 1.016; set_timing_derate -late -cell_check 1.016 }
set_input_delay 0 -clock clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 4 -clock clk [get_ports {in_valid in_vc dst_x* dst_y* in_flit* credit_ret_vc0* credit_ret_vc1*}]
set_output_delay 4 -clock clk [get_ports {in_ready out_valid* out_vc out_flit*}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n in_valid in_vc dst_x* dst_y* in_flit* credit_ret_vc0* credit_ret_vc1*}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
if {!$routed} { write_sdf -no_timestamp -digits 4 ../build/xy_router_$corner.sdf }
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns"
exit [expr {$setup < 0 || $hold < 0}]
