// Connects the cpu to riscv-formal: code memory, data memory and stream inputs take any value every cycle, reset drives rst_n, and for the liveness check (RISCV_FORMAL_FAIRNESS) the core is assumed not asleep, since only an enabled interrupt ends a wfi.
module rvfi_wrapper (
  input clock,
  input reset,
  `RVFI_OUTPUTS
);
  (* keep *) `rvformal_rand_reg [31:0] imem_data;
  (* keep *) `rvformal_rand_reg [31:0] dmem_rdata;
  (* keep *) `rvformal_rand_reg [7:0] s_tdata;
  (* keep *) `rvformal_rand_reg s_tvalid;
  (* keep *) `rvformal_rand_reg s_tlast;
  (* keep *) wire [31:0] imem_addr, dmem_addr, dmem_wdata, retire_pc, retire_instr, retire_rd_data;
  (* keep *) wire [4:0] retire_rd;
  (* keep *) wire [3:0] dmem_wstrb, retire_cause;
  (* keep *) wire imem_en, dmem_read, s_tready, retire_valid, retire_intr, sleep;
  cpu uut (
    .clk(clock), .rst_n(!reset), .imem_addr, .imem_en, .imem_data, .dmem_addr, .dmem_wdata, .dmem_wstrb, .dmem_read, .dmem_rdata,
    .s_tvalid, .s_tready, .s_tdata, .s_tlast, .retire_valid, .retire_pc, .retire_instr, .retire_rd_data, .retire_rd, .retire_intr, .sleep, .retire_cause,
    `RVFI_CONN32
  );
`ifdef RISCV_FORMAL_FAIRNESS
  always @* if (!reset) assume (!sleep);
`endif
endmodule
