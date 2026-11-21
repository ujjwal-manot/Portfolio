// CDC probe: the first synchronizer flop, which may be metastable, also feeds logic.
module meta_used (input logic a_clk, b_clk, d, output logic q, p);
  logic src, meta;
  always_ff @(posedge a_clk) src <= d;
  always_ff @(posedge b_clk) {q, meta} <= {meta, src};
  always_ff @(posedge b_clk) p <= !meta;
endmodule
