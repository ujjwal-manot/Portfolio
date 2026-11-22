// Dead-zone-free phase-frequency detector and programmable multi-modulus divider (n_int + dither_in from mash111) for projects/frac_n_pll.
module pfd_div #(
  parameter int DIV_W   = 10,
  parameter int MIN_DIV = 2
) (
  input  logic              vco_clk,
  input  logic              ref_clk,
  input  logic              rst_n,
  input  logic [DIV_W-1:0]  n_int,
  input  logic signed [3:0] dither_in,
  output logic              div_clk,
  output logic              pfd_up,
  output logic              pfd_dn,
  output logic [DIV_W-1:0]  eff_div
);
  logic [DIV_W-1:0]        cnt, next_div;
  logic signed [DIV_W:0]   raw_div;
  logic                    ref_clk_d, ref_edge, div_pulse;

  assign raw_div  = $signed({1'b0, n_int}) + $signed({{(DIV_W-3){dither_in[3]}}, dither_in});
  assign next_div = (raw_div < $signed((DIV_W+1)'(MIN_DIV))) ? DIV_W'(MIN_DIV) : raw_div[DIV_W-1:0];
  assign ref_edge = ref_clk && !ref_clk_d;

  always_ff @(posedge vco_clk or negedge rst_n) begin
    if (!rst_n) begin
      cnt       <= '0;
      eff_div   <= DIV_W'(MIN_DIV);
      div_clk   <= 1'b0;
      div_pulse <= 1'b0;
      ref_clk_d <= 1'b0;
      pfd_up    <= 1'b0;
      pfd_dn    <= 1'b0;
    end else begin
      ref_clk_d <= ref_clk;
      if (cnt + 1'b1 >= eff_div) begin
        cnt       <= '0;
        eff_div   <= next_div;
        div_clk   <= 1'b1;
        div_pulse <= 1'b1;
      end else begin
        cnt       <= cnt + 1'b1;
        div_clk   <= ((cnt + 1'b1) < (eff_div >> 1));
        div_pulse <= 1'b0;
      end
      if (pfd_up && pfd_dn) begin
        pfd_up <= ref_edge;
        pfd_dn <= div_pulse;
      end else begin
        if (ref_edge)  pfd_up <= 1'b1;
        if (div_pulse) pfd_dn <= 1'b1;
      end
    end
  end
endmodule
