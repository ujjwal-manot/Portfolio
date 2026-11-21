// CDC probe: a flop on a_clk drives the asynchronous reset of a flop on b_clk.
module reset_from_a (input logic a_clk, b_clk, d, e, output logic q);
  logic kill;
  always_ff @(posedge a_clk) kill <= e;
  always_ff @(posedge b_clk or posedge kill)
    if (kill) q <= 1'b0;
    else q <= d;
endmodule
