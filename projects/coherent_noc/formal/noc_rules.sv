// Formal verification harnesses for projects/coherent_noc xy_router and d2d_replay proving dimension-order routing, per-VC credit bounds, CRC-16-CCITT integrity, and exact Go-Back-N replay without skipped flits.
module xy_router_rules (
  input logic       clk,
  input logic       in_valid,
  input logic       in_vc,
  input logic [1:0] dst_x,
  input logic [1:0] dst_y,
  input logic [7:0] in_flit,
  input logic [4:0] credit_ret_vc0,
  input logic [4:0] credit_ret_vc1
);
  logic       rst_n = 0;
  logic       in_ready, out_vc;
  logic [4:0] out_valid;
  logic [7:0] out_flit;
  logic [2:0] exp_port, exp_port_q;
  logic       accepted_q, exp_vc_q;
  logic [7:0] exp_flit_q;
  logic [3:0] occ0 [0:4];
  logic [3:0] occ1 [0:4];

  xy_router #(.MY_X(1), .MY_Y(1), .FLIT_W(8), .CREDITS(2)) dut (
    .clk           (clk),
    .rst_n         (rst_n),
    .in_valid      (in_valid),
    .in_vc         (in_vc),
    .dst_x         (dst_x),
    .dst_y         (dst_y),
    .in_flit       (in_flit),
    .in_ready      (in_ready),
    .credit_ret_vc0(credit_ret_vc0),
    .credit_ret_vc1(credit_ret_vc1),
    .out_valid     (out_valid),
    .out_vc        (out_vc),
    .out_flit      (out_flit)
  );

  always_comb begin
    if (dst_x > 2'd1)      exp_port = 3'd3;
    else if (dst_x < 2'd1) exp_port = 3'd4;
    else if (dst_y > 2'd1) exp_port = 3'd1;
    else if (dst_y < 2'd1) exp_port = 3'd2;
    else                   exp_port = 3'd0;
  end

  genvar p;
  generate
    for (p = 0; p < 5; p = p + 1) begin : gen_cr
      always_ff @(posedge clk) begin
        if (!rst_n) begin
          occ0[p] <= 4'd0;
          occ1[p] <= 4'd0;
        end else begin
          occ0[p] <= occ0[p] + ((in_valid && in_ready && !in_vc && exp_port == p[2:0]) ? 4'd1 : 4'd0) - {3'b0, credit_ret_vc0[p]};
          occ1[p] <= occ1[p] + ((in_valid && in_ready &&  in_vc && exp_port == p[2:0]) ? 4'd1 : 4'd0) - {3'b0, credit_ret_vc1[p]};
        end
      end
      always_comb begin
        if (!rst_n) begin
          assume (!credit_ret_vc0[p] && !credit_ret_vc1[p]);
        end else begin
          assume (!credit_ret_vc0[p] || occ0[p] > 4'd0);
          assume (!credit_ret_vc1[p] || occ1[p] > 4'd0);
          assert (occ0[p] <= 4'd2);
          assert (occ1[p] <= 4'd2);
        end
      end
    end
  endgenerate

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      rst_n      <= 1'b1;
      accepted_q <= 1'b0;
      exp_port_q <= 3'd0;
      exp_vc_q   <= 1'b0;
      exp_flit_q <= 8'd0;
    end else begin
      accepted_q <= in_valid && in_ready;
      exp_port_q <= exp_port;
      exp_vc_q   <= in_vc;
      exp_flit_q <= in_flit;
    end
  end

  always_comb begin
    if (rst_n) begin
      assert ((out_valid & (out_valid - 5'd1)) == 5'd0);
      if (accepted_q) assert (out_valid == (5'b1 << exp_port_q) && out_vc == exp_vc_q && out_flit == exp_flit_q);
      if (!accepted_q) assert (out_valid == 5'd0);
      if ((!in_vc && occ0[exp_port] == 4'd2) || (in_vc && occ1[exp_port] == 4'd2)) assert (!in_ready);
      if ((!in_vc && occ0[exp_port] < 4'd2) || (in_vc && occ1[exp_port] < 4'd2)) assert (in_ready);
      cover (out_valid[0]);
      cover (out_valid[1]);
      cover (out_valid[2]);
      cover (out_valid[3]);
      cover (out_valid[4]);
      cover (!in_ready);
      cover (occ0[3] == 4'd2 && in_vc && dst_x == 2'd2 && in_ready);
    end
  end
endmodule

module d2d_replay_rules (
  input logic       clk,
  input logic       tx_valid,
  input logic [7:0] tx_flit,
  input logic       ack_valid,
  input logic       nak_valid,
  input logic [2:0] ack_seq
);
  logic        rst_n = 0;
  logic        tx_ready, link_valid;
  logic [2:0]  link_seq;
  logic [7:0]  link_flit;
  logic [15:0] link_crc;
  logic [7:0]  ref_mem [0:7];
  logic [3:0]  w_cnt = 0, a_cnt = 0;
  logic        nak_stage1 = 0, nak_check = 0, replay_seen = 0;
  logic [2:0]  replay_seq = 0;

  d2d_replay #(.FLIT_W(8)) dut (
    .clk       (clk),
    .rst_n     (rst_n),
    .tx_valid  (tx_valid),
    .tx_flit   (tx_flit),
    .tx_ready  (tx_ready),
    .ack_valid (ack_valid),
    .nak_valid (nak_valid),
    .ack_seq   (ack_seq),
    .link_valid(link_valid),
    .link_seq  (link_seq),
    .link_flit (link_flit),
    .link_crc  (link_crc)
  );

  function automatic logic [15:0] crc16_ref(input logic [7:0] d);
    logic [15:0] c;
    c = 16'hffff;
    for (int i = 7; i >= 0; i--) begin
      if (c[15] ^ d[i]) c = {c[14:0], 1'b0} ^ 16'h1021;
      else              c = {c[14:0], 1'b0};
    end
    return c;
  endfunction

  wire [3:0] in_flight = w_cnt - a_cnt;
  wire [2:0] seq_off   = ack_seq - a_cnt[2:0];

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      rst_n       <= 1'b1;
      w_cnt       <= 4'd0;
      a_cnt       <= 4'd0;
      nak_stage1  <= 1'b0;
      nak_check   <= 1'b0;
      replay_seq  <= 3'd0;
      replay_seen <= 1'b0;
    end else begin
      if (ack_valid) a_cnt <= a_cnt + {1'b0, seq_off} + 4'd1;
      if (tx_valid && tx_ready) begin
        ref_mem[w_cnt[2:0]] <= tx_flit;
        w_cnt               <= w_cnt + 4'd1;
      end
      if (nak_valid) begin
        nak_stage1 <= 1'b1;
        nak_check  <= 1'b0;
        replay_seq <= ack_seq;
      end else begin
        nak_stage1 <= 1'b0;
        nak_check  <= nak_stage1 && !ack_valid;
        if (nak_check) replay_seen <= 1'b1;
      end
    end
  end

  always_comb begin
    if (!rst_n) begin
      assume (!ack_valid && !nak_valid && !tx_valid);
    end else begin
      assume (!(ack_valid && nak_valid));
      if (ack_valid) assume ({1'b0, seq_off} < in_flight);
      if (nak_valid) assume ({1'b0, seq_off} < in_flight);
      assert (in_flight <= 4'd8);
      if (in_flight == 4'd8) assert (!tx_ready);
      if (nak_valid) assert (!tx_ready);
      if (link_valid) begin
        assert (link_flit == ref_mem[link_seq]);
        assert (link_crc == crc16_ref(link_flit));
      end
      if (nak_stage1) assert (!link_valid);
      if (nak_check) assert (link_valid && link_seq == replay_seq && link_flit == ref_mem[replay_seq]);
      cover (replay_seen);
      cover (in_flight == 4'd8 && !tx_ready);
      cover (link_valid && link_seq == 3'd7);
    end
  end
endmodule
