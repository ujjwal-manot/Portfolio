// Test board for the cpu: WORDS words of RAM (64 KB unless given) loaded from +program=<hex file>, synchronous like an SRAM macro: addresses and writes are taken at a clock edge and read data comes out in the following cycle, and the code side keeps its last word on a cycle where imem_en is low.
module cpu_board #(parameter int WORDS = 16384) (
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
  localparam int A = $clog2(WORDS);
  logic [31:0] ram [WORDS];
  logic [31:0] imem_addr, imem_data, dmem_rdata;
  logic        imem_en;
  logic        dmem_read;
  string       image;

  initial if ($value$plusargs("program=%s", image)) $readmemh(image, ram);

  logic [A-1:0] ia, da;
  assign imem_data  = ram[ia];
  assign dmem_rdata = ram[da];

  always_ff @(posedge clk) begin
    if (imem_en) ia <= imem_addr[A+1:2];
    da <= dmem_addr[A+1:2];
    if (dmem_addr < 32'(4 * WORDS))
      for (int b = 0; b < 4; b++)
        if (dmem_wstrb[b]) ram[dmem_addr[A+1:2]][8*b +: 8] <= dmem_wdata[8*b +: 8];
  end

  cpu core (.*);
endmodule
