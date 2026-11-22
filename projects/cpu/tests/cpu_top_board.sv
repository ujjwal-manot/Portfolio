// The mapped cpu_top (cells and the two SRAM macros) with the program from +program= loaded into both macros, as a boot loader would leave them.
module cpu_top_board (
  input  logic        clk, rst_n,
  input  logic        s_tvalid, s_tlast,
  input  logic [7:0]  s_tdata,
  output logic        s_tready,
  output logic        retire_valid, retire_intr, sleep,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd,
  output logic [3:0]  retire_cause
);
  cpu_top top (.*);
  string image;
  initial
    if ($value$plusargs("program=%s", image)) begin
      $readmemh(image, top.imem.i_SRAM_1P_behavioral_bm_bist.memory);
      $readmemh(image, top.dmem.i_SRAM_1P_behavioral_bm_bist.memory);
    end
endmodule
