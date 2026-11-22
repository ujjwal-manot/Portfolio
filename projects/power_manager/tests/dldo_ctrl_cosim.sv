// The digital LDO controller as ngspice d_cosim sees it: ngspice's Verilator shim takes ports of at most 64 bits, so the 128 unit enables come out as four 32-bit ports, most significant first, in the same bit order as dldo_ctrl's on.
module dldo_ctrl_cosim (
  input  logic        clk, rst_n, lo, hi, far_lo, far_hi,
  output logic [31:0] on3, on2, on1, on0,
  output logic [7:0]  count, drive
);
  dldo_ctrl #(.N(128), .BIG(8), .P(1)) ctrl (.clk, .rst_n, .lo, .hi, .far_lo, .far_hi, .on({on3, on2, on1, on0}), .count, .drive);
endmodule
