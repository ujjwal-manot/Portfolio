# Checks fifo_bridge cell timing at the corner named by CORNER (slow, typ, fast): s_clk 10 MHz, m_clk 50 MHz, every crossing between them (Gray pointers and FIFO memory) held under one m_clk period, rst_n untimed because reset_sync owns it.
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
set_load 0.01 [all_outputs]
check_setup -verbose
report_checks -path_delay max -group_path_count 3
report_checks -path_delay max -from [get_clocks s_clk] -to [get_clocks m_clk] -group_path_count 2
report_checks -path_delay max -from [get_clocks m_clk] -to [get_clocks s_clk] -group_path_count 2
report_checks -path_delay min
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
puts "corner $corner: worst setup slack $setup ns, worst hold slack $hold ns"
exit [expr {$setup < 0 || $hold < 0}]
