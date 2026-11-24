# Checks fifo_bridge timing at the corner named by CORNER (slow, typ, fast), on the mapped netlist or, when NETLIST and SPEF are set, on the routed netlist with its extracted wires and propagated clock trees: s_clk 10 MHz, m_clk 50 MHz, every crossing held under one m_clk period, rst_n untimed because reset_sync owns it, inputs driven by an IHP flop and outputs loading one IHP flop D pin, neighbours given 20% of their clock period as an interface budget, no clock jitter (no measured source exists for the input clocks); reports the Gray pointer skew (latest late arrival minus earliest early arrival at the first synchronizer flops) and, before layout, writes the corner's SDF.
set corner $::env(CORNER)
set routed [info exists ::env(SPEF)]
read_liberty ../build/$corner.lib
read_verilog [expr {$routed ? $::env(NETLIST) : "../build/fifo_bridge_cells.v"}]
link_design fifo_bridge
if {$routed} { read_spef $::env(SPEF) }
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
if {$routed} { set_propagated_clock [all_clocks] }
set_max_delay 20 -ignore_clock_latency -from [get_clocks s_clk] -to [get_clocks m_clk]
set_max_delay 20 -ignore_clock_latency -from [get_clocks m_clk] -to [get_clocks s_clk]
set_input_delay 0 -clock s_clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 20 -clock s_clk [get_ports {s_tvalid s_tdata* s_tlast}]
set_output_delay 20 -clock s_clk [get_ports s_tready]
set_input_delay 4 -clock m_clk [get_ports m_tready]
set_output_delay 4 -clock m_clk [get_ports {m_tvalid m_tdata* m_tlast}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
set bad 0
foreach {a b sync} {s_clk m_clk fifo.w_to_r.meta m_clk s_clk fifo.r_to_w.meta} {
  set ends [get_pins -of_objects [get_cells -of_objects [get_pins -of_objects [get_nets $sync*] -filter "direction==output"]] -filter "lib_pin_name==D"]
  set late {}
  set early {}
  foreach {delay into} {max late min early} {
    foreach p [find_timing_paths -path_delay $delay -from [get_clocks $a] -to $ends -group_path_count 100 -endpoint_path_count 1 -unique_paths_to_endpoint] {
      lappend $into [get_property [lindex [get_property $p points] end] arrival]
    }
  }
  set skew [expr {[tcl::mathfunc::max {*}$late] - [tcl::mathfunc::min {*}$early]}]
  set bad [expr {$bad || [llength $late] != 5 || [llength $early] != 5 || $skew >= 20}]
  puts "gray pointer $a to $b: [llength $late] bits, skew [format %.4f $skew] ns, margin [format %.4f [expr {20 - $skew}]] ns to one m_clk period"
}
set out [open ../build/clock_to_output_[expr {$routed ? "routed_" : ""}]$corner.txt w]
foreach port [get_ports {m_tvalid m_tlast m_tdata*}] {
  set net [get_nets [get_full_name $port]]
  while {[get_property [set drive [get_pins -of_objects $net -filter "direction==output"]] lib_pin_name] != "Q"} {
    set net [get_nets -of_objects [get_pins -of_objects [get_cells -of_objects $drive] -filter "lib_pin_name==A"]]
  }
  set clock [get_pins -of_objects [get_cells -of_objects $drive] -filter "lib_pin_name==CLK"]
  set edges {}
  foreach edge {rise fall} {
    lappend edges [format %.4f [get_property [lindex [get_property [find_timing_paths -path_delay max -from $clock -${edge}_to $port] points] end] arrival]]
  }
  puts $out "[get_full_name $port] $edges"
  puts "clock to output [get_full_name $port]: rise [lindex $edges 0] ns, fall [lindex $edges 1] ns after the m_clk pin edge"
}
close $out
set_false_path -hold -from [get_clocks s_clk] -to [get_clocks m_clk]
set_false_path -hold -from [get_clocks m_clk] -to [get_clocks s_clk]
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay max -from [get_clocks s_clk] -to [get_clocks m_clk] -group_path_count 2
report_checks -path_delay max -from [get_clocks m_clk] -to [get_clocks s_clk] -group_path_count 2
report_checks -path_delay min
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
if {!$routed} { write_sdf -no_timestamp -digits 4 ../build/fifo_bridge_$corner.sdf }
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns"
exit [expr {$setup < 0 || $hold < 0 || $bad}]
