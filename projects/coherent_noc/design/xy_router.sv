// Dimension-order X-then-Y mesh router head-flit allocator with 2 virtual channels (REQ=0, RSP=1) and per-output credit tracking for projects/coherent_noc.
module xy_router #(
  parameter int MY_X = 0,
  parameter int MY_Y = 0,
  parameter int FLIT_W = 32,
  parameter int CREDITS = 4
) (
  input  logic                clk,
  input  logic                rst_n,
  input  logic                in_valid,
  input  logic                in_vc,
  input  logic [1:0]          dst_x,
  input  logic [1:0]          dst_y,
  input  logic [FLIT_W-1:0]   in_flit,
  output logic                in_ready,
  input  logic [4:0]          credit_ret_vc0,
  input  logic [4:0]          credit_ret_vc1,
  output logic [4:0]          out_valid,
  output logic                out_vc,
  output logic [FLIT_W-1:0]   out_flit
);
  logic [2:0]  out_port;
  logic [3:0]  cr [5][2];
  logic        has_credit;

  always_comb begin
    if (int'(dst_x) > MY_X)      out_port = 3'd3;
    else if (int'(dst_x) < MY_X) out_port = 3'd4;
    else if (int'(dst_y) > MY_Y) out_port = 3'd1;
    else if (int'(dst_y) < MY_Y) out_port = 3'd2;
    else                         out_port = 3'd0;
    has_credit = (cr[out_port][in_vc] != 4'd0);
    in_ready   = has_credit;
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      out_valid <= 5'b0;
      out_vc    <= 1'b0;
      out_flit  <= '0;
      for (int p = 0; p < 5; p++) begin
        cr[p][0] <= 4'(CREDITS);
        cr[p][1] <= 4'(CREDITS);
      end
    end else begin
      out_valid <= 5'b0;
      if (in_valid && has_credit) begin
        out_valid[out_port] <= 1'b1;
        out_vc              <= in_vc;
        out_flit            <= in_flit;
      end
      for (int p = 0; p < 5; p++) begin
        cr[p][0] <= cr[p][0] + {3'b0, credit_ret_vc0[p]} - ((in_valid && has_credit && !in_vc && int'(out_port) == p) ? 4'd1 : 4'd0);
        cr[p][1] <= cr[p][1] + {3'b0, credit_ret_vc1[p]} - ((in_valid && has_credit &&  in_vc && int'(out_port) == p) ? 4'd1 : 4'd0);
      end
    end
  end
endmodule
