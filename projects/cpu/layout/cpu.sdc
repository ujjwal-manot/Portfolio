# Constraints for the cpu_top layout, the same as timing/timing.tcl: 50 MHz, the stream inputs valid 16 ns into the cycle and s_tready needed 4 ns before its end (the split fifo_bridge checks its side against), rst_n untimed into reset_sync (it releases asynchronously there) and the synchronized reset timed through its buffer tree to every flop, inputs driven by an IHP flop, outputs loading one IHP flop D pin, retire_* and sleep (testbench ports) untimed.
create_clock -name clk -period 20 [get_ports clk]
set_input_delay 16 -clock clk [get_ports {s_tvalid s_tdata* s_tlast}]
set_input_delay 0 -clock clk [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_output_delay 16 -clock clk [get_ports s_tready]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
set_false_path -to [get_ports {retire* sleep}]
