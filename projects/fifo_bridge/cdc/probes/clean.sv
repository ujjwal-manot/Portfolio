// CDC probe with nothing wrong: one bit through a two-flop synchronizer.
module clean (input logic a_clk, b_clk, d, output logic q);
  logic src, meta;
  always_ff @(posedge a_clk) src <= d;
  always_ff @(posedge b_clk) {q, meta} <= {meta, src};
endmodule
