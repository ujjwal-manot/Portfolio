# Reports sar_logic power at the corner named by CORNER (slow, typ, fast) from the switching in the VCD named by VCD, recorded by that corner's SDF-timed gate-level run of the calibration and the ideal-quantizer conversion (so glitches count), with a 10 MHz clock and the same drivers and output load as timing.tcl.
set corner $::env(CORNER)
read_liberty ../build/$corner.lib
read_verilog ../build/sar_logic_cells.v
link_design sar_logic
create_clock -name clk -period 100 [get_ports clk]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n comp_out m_tready}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
read_vcd -scope sar_logic $::env(VCD)
report_activity_annotation
report_power
