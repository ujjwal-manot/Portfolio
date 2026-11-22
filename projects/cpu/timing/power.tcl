# Reports cpu_top power at the typical corner (1.20 V, 25 C) from the switching recorded in build/cpu_gates.vcd, the filter firmware at full stream rate on the mapped netlist with the SRAM macros' own models (zero delay, so glitches are left out), with the 50 MHz clock ideal (no clock tree yet) and the stream inputs driven by an IHP flop.
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_liberty /foss/pdks/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x32_c2_bm_bist_typ_1p20V_25C.lib
read_verilog ../build/cpu_cells.v
link_design cpu_top
create_clock -name clk -period 20 [get_ports clk]
set_driving_cell -lib_cell sg13g2_dfrbpq_1 -pin Q [get_ports {rst_n s_tvalid s_tdata* s_tlast}]
read_vcd -scope cpu_top_board/top ../build/cpu_gates.vcd
report_activity_annotation
report_power
report_power -instances [get_cells {imem dmem}]
