// The cpu with its two memories as the IHP SRAM macros (2048 x 32 each, 8 KB of code and 8 KB of data), wired as the core expects: instruction macro reading at imem_addr only on cycles where the core asks (imem_en: the fetch address changed), else idle and holding its last word, data macro reading and writing the strobed bytes only when the address is in RAM (a load from the stream, counters or timer at 0x1000_0000 leaves it idle); BIST ports tied off.
module cpu_top (
  input  logic        clk, rst_n,
  input  logic        s_tvalid, s_tlast,
  input  logic [7:0]  s_tdata,
  output logic        s_tready,
  output logic        retire_valid, retire_intr, sleep,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd,
  output logic [3:0]  retire_cause
);
  logic [31:0] imem_addr, imem_data, dmem_addr, dmem_wdata, dmem_rdata;
  logic        imem_en;
  logic [3:0]  dmem_wstrb;
  logic        dmem_read;
  wire         ram = dmem_addr[31:13] == 0;
  cpu core (.*);
  RM_IHPSG13_1P_2048x32_c2_bm_bist imem (.A_CLK(clk), .A_MEN(imem_en), .A_WEN(1'b0), .A_REN(1'b1), .A_ADDR(imem_addr[12:2]), .A_DIN(32'b0), .A_DLY(1'b1),
    .A_DOUT(imem_data), .A_BM(32'b0), .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0), .A_BIST_WEN(1'b0), .A_BIST_REN(1'b0),
    .A_BIST_ADDR(11'b0), .A_BIST_DIN(32'b0), .A_BIST_BM(32'b0));
  RM_IHPSG13_1P_2048x32_c2_bm_bist dmem (.A_CLK(clk), .A_MEN(1'b1), .A_WEN(ram && |dmem_wstrb), .A_REN(ram && dmem_read), .A_ADDR(dmem_addr[12:2]), .A_DIN(dmem_wdata), .A_DLY(1'b1),
    .A_DOUT(dmem_rdata), .A_BM({{8{dmem_wstrb[3]}}, {8{dmem_wstrb[2]}}, {8{dmem_wstrb[1]}}, {8{dmem_wstrb[0]}}}), .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0),
    .A_BIST_WEN(1'b0), .A_BIST_REN(1'b0), .A_BIST_ADDR(11'b0), .A_BIST_DIN(32'b0), .A_BIST_BM(32'b0));
endmodule
