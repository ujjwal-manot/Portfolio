# Reports sar_logic power at the typical corner from the switching recorded in build/sar_gates.vcd, the ideal-quantizer conversion run on the mapped netlist (zero-delay, so glitches are left out), with a 10 MHz clock and outputs loading one IHP flop D pin.
read_liberty ../build/typ.lib
read_verilog ../build/sar_logic_cells.v
link_design sar_logic
create_clock -name clk -period 100 [get_ports clk]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
read_vcd -scope sar_logic ../build/sar_gates.vcd
report_activity_annotation
report_power
