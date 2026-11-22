// Die-to-die flit transmitter with CRC-16-CCITT (0x1021) and an 8-slot go-back-N replay buffer for projects/coherent_noc.
module d2d_replay #(
  parameter int FLIT_W = 32
) (
  input  logic                clk,
  input  logic                rst_n,
  input  logic                tx_valid,
  input  logic [FLIT_W-1:0]   tx_flit,
  output logic                tx_ready,
  input  logic                ack_valid,
  input  logic                nak_valid,
  input  logic [2:0]          ack_seq,
  output logic                link_valid,
  output logic [2:0]          link_seq,
  output logic [FLIT_W-1:0]   link_flit,
  output logic [15:0]         link_crc
);
  logic [FLIT_W-1:0] buf_mem [8];
  logic [3:0]        wptr, rptr, aptr;
  logic              full, has_pending;

  function automatic logic [15:0] crc16_word(input logic [FLIT_W-1:0] d);
    logic [15:0] c;
    c = 16'hffff;
    for (int i = FLIT_W - 1; i >= 0; i--) begin
      if (c[15] ^ d[i]) c = {c[14:0], 1'b0} ^ 16'h1021;
      else              c = {c[14:0], 1'b0};
    end
    return c;
  endfunction

  assign full        = (wptr - aptr) >= 4'd8;
  assign tx_ready    = !full && !nak_valid;
  assign has_pending = (rptr != wptr);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wptr       <= 4'd0;
      rptr       <= 4'd0;
      aptr       <= 4'd0;
      link_valid <= 1'b0;
      link_seq   <= 3'd0;
      link_flit  <= '0;
      link_crc   <= 16'd0;
    end else begin
      if (ack_valid) aptr <= {aptr[3], ack_seq} + 4'd1;
      if (tx_valid && tx_ready) begin
        buf_mem[wptr[2:0]] <= tx_flit;
        wptr               <= wptr + 4'd1;
      end
      if (nak_valid) begin
        rptr       <= {aptr[3], ack_seq};
        link_valid <= 1'b0;
      end else if (has_pending) begin
        link_valid <= 1'b1;
        link_seq   <= rptr[2:0];
        link_flit  <= buf_mem[rptr[2:0]];
        link_crc   <= crc16_word(buf_mem[rptr[2:0]]);
        rptr       <= rptr + 4'd1;
      end else begin
        link_valid <= 1'b0;
      end
    end
  end
endmodule
