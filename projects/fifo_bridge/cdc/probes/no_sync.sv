// CDC probe: a flop on b_clk samples a flop on a_clk straight into logic, with no synchronizer.
module no_sync (input logic a_clk, b_clk, d, e, output logic q);
  logic src;
  always_ff @(posedge a_clk) src <= d;
  always_ff @(posedge b_clk) q <= src & e;
endmodule
