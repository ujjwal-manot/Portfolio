# Reports fifo_bridge power at the corner named by CORNER (slow, typ, fast) from the switching in the VCD named by VCD, recorded by that corner's SDF-timed gate-level run of the 1 MS/s ADC-sample test, with the same port load and drivers as timing.tcl; when NETLIST and SPEF are set it reads the routed netlist with its extracted wires, so the clock trees and wire capacitance count.
set corner $::env(CORNER)
set routed [info exists ::env(SPEF)]
read_liberty ../build/$corner.lib
read_verilog [expr {$routed ? $::env(NETLIST) : "../build/fifo_bridge_cells.v"}]
link_design fifo_bridge
if {$routed} { read_spef $::env(SPEF) }
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
if {$routed} { set_propagated_clock [all_clocks] }
set_clock_groups -asynchronous -group s_clk -group m_clk
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
read_vcd -scope fifo_bridge $::env(VCD)
report_activity_annotation
report_power
