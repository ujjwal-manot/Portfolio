// CDC probe: two a_clk flops are combined before the first synchronizer flop, so a glitch can be captured.
module logic_before_sync (input logic a_clk, b_clk, d, e, output logic q);
  logic x, y, meta;
  always_ff @(posedge a_clk) {x, y} <= {d, e};
  always_ff @(posedge b_clk) {q, meta} <= {meta, x & y};
endmodule
