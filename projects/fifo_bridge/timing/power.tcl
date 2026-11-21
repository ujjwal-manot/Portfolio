# Reports fifo_bridge power at the typical corner (1.2 V, 25 C) from the switching recorded in the gate-level simulation of the 10 MHz to 50 MHz test.
read_liberty ../build/typ.lib
read_verilog ../build/fifo_bridge_cells.v
link_design fifo_bridge
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
set_clock_groups -asynchronous -group s_clk -group m_clk
read_vcd -scope fifo_bridge ../build/gates.vcd
report_activity_annotation
report_power
