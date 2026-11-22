// Test board for the cpu: 64 KB RAM loaded from +program=<hex file>, synchronous like an SRAM macro: addresses and writes are taken at a clock edge and read data comes out in the following cycle, and the code side keeps its last word on a cycle where imem_en is low.
module cpu_board (
  input  logic        clk, rst_n,
  input  logic        s_tvalid, s_tlast,
  input  logic [7:0]  s_tdata,
  output logic        s_tready,
  output logic        retire_valid,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd,
  output logic        retire_intr, sleep,
  output logic [3:0]  retire_cause,
  output logic [31:0] dmem_addr, dmem_wdata,
  output logic [3:0]  dmem_wstrb
);
  logic [31:0] ram [16384];
  logic [31:0] imem_addr, imem_data, dmem_rdata;
  logic        imem_en;
  logic        dmem_read;
  string       image;

  initial if ($value$plusargs("program=%s", image)) $readmemh(image, ram);

  logic [13:0] ia, da;
  assign imem_data  = ram[ia];
  assign dmem_rdata = ram[da];

  always_ff @(posedge clk) begin
    if (imem_en) ia <= imem_addr[15:2];
    da <= dmem_addr[15:2];
    if (dmem_addr[31:16] == 0)
      for (int b = 0; b < 4; b++)
        if (dmem_wstrb[b]) ram[dmem_addr[15:2]][8*b +: 8] <= dmem_wdata[8*b +: 8];
  end

  cpu core (.*);
endmodule
