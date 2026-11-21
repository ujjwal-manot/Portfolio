# Checks fifo_bridge cell timing at the corner named by CORNER (slow, typ, fast): s_clk 10 MHz, m_clk 50 MHz, every crossing held under one m_clk period, rst_n untimed because reset_sync owns it, inputs driven by an IHP flop and outputs loading one IHP flop D pin (no wire load until layout), neighbours given 20% of their clock period as an interface budget, no clock jitter until frac_n_pll exists; reports the Gray pointer skew and writes the corner's SDF, plus a copy for Icarus without the port wires it cannot place (before layout these carry only the input driver delay, which STA here still counts).
set corner $::env(CORNER)
read_liberty ../build/$corner.lib
read_verilog ../build/fifo_bridge_cells.v
link_design fifo_bridge
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
set_max_delay 20 -ignore_clock_latency -from [get_clocks s_clk] -to [get_clocks m_clk]
set_max_delay 20 -ignore_clock_latency -from [get_clocks m_clk] -to [get_clocks s_clk]
set_false_path -hold -from [get_clocks s_clk] -to [get_clocks m_clk]
set_false_path -hold -from [get_clocks m_clk] -to [get_clocks s_clk]
set_input_delay 0 -clock s_clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 20 -clock s_clk [get_ports {s_tvalid s_tdata* s_tlast}]
set_output_delay 20 -clock s_clk [get_ports s_tready]
set_input_delay 4 -clock m_clk [get_ports m_tready]
set_output_delay 4 -clock m_clk [get_ports {m_tvalid m_tdata* m_tlast}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay max -from [get_clocks s_clk] -to [get_clocks m_clk] -group_path_count 2
report_checks -path_delay max -from [get_clocks m_clk] -to [get_clocks s_clk] -group_path_count 2
report_checks -path_delay min
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
set bad 0
foreach {a b} {s_clk m_clk m_clk s_clk} {
  set t {}
  foreach p [find_timing_paths -from [get_clocks $a] -to [get_clocks $b] -group_path_count 1000 -endpoint_path_count 1 -unique_paths_to_endpoint] {
    set pts [get_property $p points]
    if {[llength $pts] == 2} { lappend t [get_property [lindex $pts end] arrival] }
  }
  set skew [expr {[tcl::mathfunc::max {*}$t] - [tcl::mathfunc::min {*}$t]}]
  set bad [expr {$bad || [llength $t] != 5 || $skew >= 20}]
  puts "gray pointer $a to $b: [llength $t] bits, skew [format %.4f $skew] ns, margin [format %.4f [expr {20 - $skew}]] ns to one m_clk period"
}
set sdf ../build/fifo_bridge_$corner.sdf
write_sdf -no_timestamp -digits 4 $sdf
set f [open $sdf]; set lines [split [read $f] \n]; close $f
set f [open ../build/fifo_bridge_${corner}_sim.sdf w]; puts -nonewline $f [join [lsearch -all -inline -not -regexp $lines {INTERCONNECT ([^/ ]+ \S+|\S+ [^/ ]+) \(}] \n]; close $f
puts "corner $corner: worst setup slack $setup ns, worst hold slack $hold ns"
exit [expr {$setup < 0 || $hold < 0 || $bad}]
