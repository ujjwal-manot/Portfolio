// CDC probe: a 4-bit binary counter crosses bit by bit through two-flop synchronizers, so bits can arrive from different counts.
module binary_bus (input logic a_clk, b_clk, output logic [3:0] q);
  logic [3:0] count = '0, meta;
  always_ff @(posedge a_clk) count <= count + 1;
  always_ff @(posedge b_clk) {q, meta} <= {meta, count};
endmodule
