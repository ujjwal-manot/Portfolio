# Checks whole_chip_top timing at the corner in CORNER (slow: 1.08 V 125 C with 1.016 cold-slow derate from power_manager/results/speed.log, typ: 1.20 V 25 C, fast: 1.32 V -40 C) across clk_adc (10 MHz, 100 ns) and clk_sys (50 MHz, 20 ns) with 20 ns max-delay CDC bounds on fifo_bridge crossings.
set corner $::env(CORNER)
set cells [dict get {slow slow_1p08V_125C typ typ_1p20V_25C fast fast_1p32V_m40C} $corner]
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_$cells.lib
read_verilog ../build/whole_chip_top_cells.v
link_design whole_chip_top
create_clock -name clk_adc -period 100 [get_ports clk_adc]
create_clock -name clk_sys -period 20 [get_ports clk_sys]
set_max_delay 20 -ignore_clock_latency -from [get_clocks clk_adc] -to [get_clocks clk_sys]
set_max_delay 20 -ignore_clock_latency -from [get_clocks clk_sys] -to [get_clocks clk_adc]
set_false_path -hold -from [get_clocks clk_adc] -to [get_clocks clk_sys]
set_false_path -hold -from [get_clocks clk_sys] -to [get_clocks clk_adc]
if {$corner == "slow"} { set_timing_derate -late -cell_delay 1.016; set_timing_derate -late -cell_check 1.016 }
set_input_delay 0 -clock clk_sys [get_ports rst_n]
set_false_path -from [get_ports rst_n]
set_input_delay 20 -clock clk_adc [get_ports comp_out]
set_output_delay 20 -clock clk_adc [get_ports {adc_samp adc_comp_clk adc_dac* adc_overflow}]
set_input_delay 4 -clock clk_sys [get_ports {dldo_lo dldo_hi dldo_far_lo dldo_far_hi droop_alert}]
set_output_delay 4 -clock clk_sys [get_ports {dvfs_state* fir_last* peak_last* cpu_sleep dldo_on*}]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n comp_out dldo_lo dldo_hi dldo_far_lo dldo_far_hi droop_alert}]
set_load [get_property [lindex [get_lib_pins */sg13g2_dfrbpq_1/D] 0] capacitance] [all_outputs]
report_checks -path_delay max -group_path_count 3
report_checks -path_delay min -group_path_count 3
set setup [expr {[sta::worst_slack_cmd max] * 1e9}]
set hold [expr {[sta::worst_slack_cmd min] * 1e9}]
puts "corner $corner: worst setup slack [format %.4f $setup] ns, worst hold slack [format %.4f $hold] ns"
exit [expr {$setup < 0}]
