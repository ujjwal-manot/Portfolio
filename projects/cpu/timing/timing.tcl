# Checks the cpu with its two SRAM macros at the corner in CORNER (slow: 1.08 V 125 C, typ: 1.2 V 25 C, fast: 1.32 V -40 C for the cells, -55 C for the macros, the nearest IHP ships) and 50 MHz: the memory paths use the macros' own liberty setup, hold and access times; the stream wires to fifo_bridge use the same split fifo_bridge's timing.tcl checks its side against (its outputs valid 16 ns into the cycle, the cpu's s_tready back within 4 ns), driven and loaded by the fifo's sg13g2_dfrbpq_1 flops; retire_* is a testbench port and is not timed; the run fails on setup only, since hold at the macro inputs (0.84 ns of library hold time at the slow corner) needs the clock tree and hold repair of a layout run.
set corner $env(CORNER)
set cells [dict get {slow slow_1p08V_125C typ typ_1p20V_25C fast fast_1p32V_m40C} $corner]
set macro [dict get {slow slow_1p08V_125C typ typ_1p20V_25C fast fast_1p32V_m55C} $corner]
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_$cells.lib
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x32_c2_bm_bist_$macro.lib
read_verilog ../build/cpu_cells.v

link_design cpu_top
create_clock -name clk -period 20 [get_ports clk]
set_input_delay 16 -clock clk [get_ports {s_tvalid s_tdata* s_tlast}]
set_input_delay 0 -clock clk [get_ports rst_n]
set_output_delay 16 -clock clk [get_ports s_tready]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [get_ports s_tready]
set_false_path -to [get_ports {retire* sleep}]
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
puts "$corner: worst setup slack $setup ns, worst hold slack $hold ns before layout (no clock tree, no hold repair; hold is signed off after layout)"
exit [expr {$setup < 0}]
