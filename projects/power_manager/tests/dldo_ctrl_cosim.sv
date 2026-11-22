// The digital LDO controller as ngspice d_cosim sees it: ngspice's Verilator shim takes ports of at most 64 bits and lists them grouped by storage width (8-bit ports before 32-bit ones, whatever the declaration order), so every port here is 8 bits or less and they keep their declared order: the 128 unit enables as sixteen bytes, most significant first, then count and drive; make cosim checks the order by running it.
module dldo_ctrl_cosim (
  input  logic       clk, rst_n, lo, hi, far_lo, far_hi,
  output logic [7:0] on15, on14, on13, on12, on11, on10, on9, on8, on7, on6, on5, on4, on3, on2, on1, on0,
  output logic [7:0] count, drive
);
  dldo_ctrl #(.N(128), .BIG(8), .P(1)) ctrl (.clk, .rst_n, .lo, .hi, .far_lo, .far_hi,
    .on({on15, on14, on13, on12, on11, on10, on9, on8, on7, on6, on5, on4, on3, on2, on1, on0}), .count, .drive);
endmodule
