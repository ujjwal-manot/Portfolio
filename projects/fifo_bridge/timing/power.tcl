# Reports fifo_bridge power at the corner named by CORNER (slow, typ, fast) from the switching recorded in that corner's SDF-timed gate-level run of the 1 MS/s ADC-sample test, with the same port load and drivers as timing.tcl; no clock tree until layout.
set corner $::env(CORNER)
read_liberty ../build/$corner.lib
read_verilog ../build/fifo_bridge_cells.v
link_design fifo_bridge
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
set_clock_groups -asynchronous -group s_clk -group m_clk
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
read_vcd -scope fifo_bridge ../build/gates_$corner.vcd
report_activity_annotation
report_power
