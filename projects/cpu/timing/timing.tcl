# Checks cpu cell timing at the slow corner and 50 MHz; the outside RAM gets 8 ns of each 20 ns cycle, the core gets the rest.
read_liberty ../build/slow.lib
read_verilog ../build/cpu_cells.v
link_design cpu
create_clock -name clk -period 20 [get_ports clk]
set_output_delay 14 -clock clk [get_ports {imem_addr* dmem_addr* dmem_wdata* dmem_wstrb* dmem_read s_tready}]
set_input_delay 14 -clock clk [get_ports {imem_data* dmem_rdata* s_tvalid s_tdata* s_tlast}]
set_output_delay 4 -clock clk [get_ports retire*]
set_load 0.01 [all_outputs]
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
puts "worst setup slack $setup ns, worst hold slack $hold ns"
exit [expr {$setup < 0 || $hold < 0}]
