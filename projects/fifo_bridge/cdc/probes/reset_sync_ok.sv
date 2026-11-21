// CDC probe with nothing wrong: an outside reset asserts at once and is released through two flops on b_clk.
module reset_sync_ok (input logic b_clk, rst_n, d, output logic q);
  logic meta, safe_n;
  always_ff @(posedge b_clk or negedge rst_n)
    if (!rst_n) {safe_n, meta} <= '0;
    else {safe_n, meta} <= {meta, 1'b1};
  always_ff @(posedge b_clk or negedge safe_n)
    if (!safe_n) q <= 1'b0;
    else q <= d;
endmodule
