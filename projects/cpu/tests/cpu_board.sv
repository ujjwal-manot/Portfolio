// Test board for the cpu: 64 KB RAM loaded from +program=<hex file>, answering in the same cycle the core asks.
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
  logic        dmem_read;
  string       image;

  initial if ($value$plusargs("program=%s", image)) $readmemh(image, ram);

  assign imem_data  = ram[imem_addr[15:2]];
  assign dmem_rdata = ram[dmem_addr[15:2]];

  always_ff @(posedge clk)
    if (dmem_addr[31:16] == 0)
      for (int b = 0; b < 4; b++)
        if (dmem_wstrb[b]) ram[dmem_addr[15:2]][8*b +: 8] <= dmem_wdata[8*b +: 8];

  cpu core (.*);
endmodule
