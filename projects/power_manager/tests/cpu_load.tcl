# Reports the cpu's power in one-cycle windows of the gate-level filter run (CPU_VCD on the mapped netlist CPU_CELLS, typical library at 1.2 V and 25 C, as projects/cpu/timing/power.tcl does for the whole run): window k runs from 20k + 5 ns to 20k + 25 ns, between clock edges, so it holds exactly one rising and one falling edge; cycles 0 to 3 are under reset (clock running, logic held), the rest run the firmware.
read_liberty $::env(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_liberty $::env(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x32_c2_bm_bist_typ_1p20V_25C.lib
read_verilog $::env(CPU_CELLS)
link_design cpu_top
create_clock -name clk -period 20 [get_ports clk]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast}]
for {set k 0} {$k < 128} {incr k} {
  set begin [expr {(20 * $k + 5) * 1000000}]
  read_vcd -scope cpu_top_board/top -begin_time $begin -end_time [expr {$begin + 20000000}] $::env(CPU_VCD)
  puts "window $k [expr {20 * $k + 5}] [expr {20 * $k + 25}]"
  report_power
}
