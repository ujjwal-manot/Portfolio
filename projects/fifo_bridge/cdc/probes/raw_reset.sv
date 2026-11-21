// CDC probe: an outside reset releases b_clk flops directly, with no reset synchronizer.
module raw_reset (input logic b_clk, rst_n, d, output logic q);
  always_ff @(posedge b_clk or negedge rst_n)
    if (!rst_n) q <= 1'b0;
    else q <= d;
endmodule
