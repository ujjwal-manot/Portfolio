# Checks fifo_bridge cell timing at the slow corner: s_clk 10 MHz, m_clk 50 MHz, the two clocks unrelated.
read_liberty ../build/slow.lib
read_verilog ../build/fifo_bridge_cells.v
link_design fifo_bridge
create_clock -name s_clk -period 100 [get_ports s_clk]
create_clock -name m_clk -period 20 [get_ports m_clk]
set_clock_groups -asynchronous -group s_clk -group m_clk
set_input_delay 20 -clock s_clk [get_ports {s_tvalid s_tdata* s_tlast}]
set_output_delay 20 -clock s_clk [get_ports s_tready]
set_input_delay 4 -clock m_clk [get_ports m_tready]
set_output_delay 4 -clock m_clk [get_ports {m_tvalid m_tdata* m_tlast}]
set_load 0.01 [all_outputs]
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
puts "worst setup slack $setup ns, worst hold slack $hold ns"
exit [expr {$setup < 0 || $hold < 0}]
