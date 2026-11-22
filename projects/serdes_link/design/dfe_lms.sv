// 1-tap decision feedback equalizer with saturating sign-sign LMS tap adaptation for projects/serdes_link.
module dfe_lms #(
  parameter int W = 10,
  parameter logic signed [W-1:0] TARGET_AMP = 10'sd64
) (
  input  logic                   clk,
  input  logic                   rst_n,
  input  logic                   en,
  input  logic signed [W-1:0]    sample_in,
  output logic                   bit_out,
  output logic signed [W-1:0]    h1_tap
);
  logic signed [W:0]   eq_sum, err_val, next_h1;
  logic                prev_bit, cur_bit, err_pos, same_sign;
  logic signed [W-1:0] h1_sat;

  assign eq_sum    = {sample_in[W-1], sample_in} - (prev_bit ? {h1_tap[W-1], h1_tap} : -{h1_tap[W-1], h1_tap});
  assign cur_bit   = !eq_sum[W];
  assign err_val   = eq_sum - (cur_bit ? {TARGET_AMP[W-1], TARGET_AMP} : -{TARGET_AMP[W-1], TARGET_AMP});
  assign err_pos   = !err_val[W];
  assign same_sign = (err_pos == prev_bit);
  assign next_h1   = {h1_tap[W-1], h1_tap} + (same_sign ? 11'sd1 : -11'sd1);
  assign h1_sat    = (next_h1 > 11'sd127) ? 10'sd127 : (next_h1 < -11'sd127) ? -10'sd127 : next_h1[W-1:0];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      prev_bit <= 1'b0;
      bit_out  <= 1'b0;
      h1_tap   <= '0;
    end else if (en) begin
      bit_out  <= cur_bit;
      prev_bit <= cur_bit;
      h1_tap   <= h1_sat;
    end
  end
endmodule
