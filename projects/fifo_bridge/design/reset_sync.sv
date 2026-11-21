// Reset synchronizer: the output reset asserts at once with the input and releases two clock edges after it, on this clock.
module reset_sync (
  input  logic clk, rst_n_in,
  output logic rst_n
);
  logic meta;
  always_ff @(posedge clk or negedge rst_n_in)
    if (!rst_n_in) {rst_n, meta} <= '0;
    else {rst_n, meta} <= {meta, 1'b1};
endmodule
