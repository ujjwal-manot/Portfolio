// Synthesizable 3rd-order MASH-111 digital sigma-delta modulator for frac_n_pll: converts a W-bit fractional divide input into signed 4-bit integer dither (-3 to +4) with 3rd-order (1 - z^-1)^3 quantization noise shaping.
module mash111 #(
  parameter int W = 20
) (
  input  logic               clk,
  input  logic               rst_n,
  input  logic [W-1:0]       frac_in,
  output logic signed [3:0]  dither_out
);
  logic [W-1:0] acc1, acc2, acc3;
  logic [W:0]   sum1, sum2, sum3;
  logic         c1, c2, c3, c2_d1, c3_d1, c3_d2;
  logic signed [3:0] s1, s2, s3;

  assign sum1 = {1'b0, acc1} + {1'b0, frac_in};
  assign sum2 = {1'b0, acc2} + {1'b0, sum1[W-1:0]};
  assign sum3 = {1'b0, acc3} + {1'b0, sum2[W-1:0]};

  assign c1 = sum1[W];
  assign c2 = sum2[W];
  assign c3 = sum3[W];

  assign s1 = {3'b0, c1};
  assign s2 = {3'b0, c2} - {3'b0, c2_d1};
  assign s3 = {3'b0, c3} - ({3'b0, c3_d1} <<< 1) + {3'b0, c3_d2};

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      acc1       <= {{(W-1){1'b0}}, 1'b1};
      acc2       <= '0;
      acc3       <= '0;
      c2_d1      <= 1'b0;
      c3_d1      <= 1'b0;
      c3_d2      <= 1'b0;
      dither_out <= 4'sd0;
    end else begin
      acc1       <= sum1[W-1:0];
      acc2       <= sum2[W-1:0];
      acc3       <= sum3[W-1:0];
      c2_d1      <= c2;
      c3_d1      <= c3;
      c3_d2      <= c3_d1;
      dither_out <= s1 + s2 + s3;
    end
  end
endmodule
