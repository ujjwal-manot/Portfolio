// Port list of the IHP SRAM macro RM_IHPSG13_1P_2048x32_c2_bm_bist, copied from its PDK model, so the layout flow sees it as a black box placed from its LEF and timed from its liberty.
(* blackbox *)
module RM_IHPSG13_1P_2048x32_c2_bm_bist (
  input A_CLK, A_MEN, A_WEN, A_REN,
  input [10:0] A_ADDR,
  input [31:0] A_DIN,
  input A_DLY,
  output [31:0] A_DOUT,
  input [31:0] A_BM,
  input A_BIST_CLK, A_BIST_EN, A_BIST_MEN, A_BIST_WEN, A_BIST_REN,
  input [10:0] A_BIST_ADDR,
  input [31:0] A_BIST_DIN,
  input [31:0] A_BIST_BM
);
endmodule
