// Formal rules for async_fifo, skid_buffer and fifo_bridge: no overflow or underflow, every word arrives intact, outputs hold while stalled.
module fifo_rules #(
  parameter int A = 2
) (
  input logic       w_clk, r_clk, w_en, r_en,
  input logic [8:0] w_data
);
  logic       w_full, r_empty, w_rst_n = 0, r_rst_n = 0;
  logic [8:0] r_data, kept;
  logic [A+1:0] writes = 0, reads = 0;
  (* anyconst *) logic [A+1:0] pick;
  wire  [A+1:0] inside = writes - reads;

  async_fifo #(.WIDTH(9), .DEPTH_LOG2(A)) dut (.*);

  always_ff @(posedge w_clk) begin
    w_rst_n <= 1;
    if (w_rst_n && w_en && !w_full) begin
      writes <= writes + 1;
      if (writes == pick) kept <= w_data;
    end
  end

  always_ff @(posedge r_clk) begin
    r_rst_n <= 1;
    if (r_rst_n && r_en && !r_empty) begin
      reads <= reads + 1;
      if (reads == pick) begin
        assert (r_data == kept);
        cover (pick == 5);
      end
    end
  end

  always_comb begin
    assert (inside <= 2**A);
    if (inside == 2**A) assert (w_full);
    if (inside == 0) assert (r_empty);
    cover (inside == 2**A && reads > 2);
  end
endmodule

module bridge_rules #(
  parameter int A = 2
) (
  input logic       s_clk, m_clk, s_tvalid, s_tlast, m_tready,
  input logic [7:0] s_tdata
);
  logic       s_tready, m_tvalid, m_tlast, s_rst_n = 0, m_rst_n = 0, stalled = 0;
  logic [7:0] m_tdata;
  logic [8:0] kept, held;
  logic [A+1:0] sent = 0, got = 0;
  (* anyconst *) logic [A+1:0] pick;
  wire  [A+1:0] inside = sent - got;

  fifo_bridge #(.DEPTH_LOG2(A)) dut (.*);

  always_ff @(posedge s_clk) begin
    s_rst_n <= 1;
    if (s_rst_n && s_tvalid && s_tready) begin
      sent <= sent + 1;
      if (sent == pick) kept <= {s_tlast, s_tdata};
    end
  end

  always_ff @(posedge m_clk) begin
    m_rst_n <= 1;
    if (stalled) begin
      assert (m_tvalid && {m_tlast, m_tdata} == held);
      cover (got > 2);
    end
    stalled <= m_rst_n && m_tvalid && !m_tready;
    held <= {m_tlast, m_tdata};
    if (m_rst_n && m_tvalid && m_tready) begin
      got <= got + 1;
      if (got == pick) begin
        assert ({m_tlast, m_tdata} == kept);
        cover (pick == 7 && m_tlast);
      end
    end
  end

  always_comb begin
    assert (inside <= 2**A + 2);
    if (inside == 0) assert (!m_tvalid);
    cover (inside == 2**A + 2);
  end
endmodule

module skid_rules (
  input logic       clk, s_valid, m_ready,
  input logic [8:0] s_data
);
  logic       rst_n = 0, s_ready, m_valid, stalled = 0;
  logic [8:0] m_data, kept, held;
  logic [3:0] sent = 0, got = 0;
  (* anyconst *) logic [3:0] pick;
  wire  [3:0] inside = sent - got;

  skid_buffer #(.WIDTH(9)) dut (.*);

  always_ff @(posedge clk) begin
    rst_n <= 1;
    if (rst_n && s_valid && s_ready) begin
      sent <= sent + 1;
      if (sent == pick) kept <= s_data;
    end
    if (stalled) begin
      assert (m_valid && m_data == held);
      cover (got > 2);
    end
    stalled <= rst_n && m_valid && !m_ready;
    held <= m_data;
    if (rst_n && m_valid && m_ready) begin
      got <= got + 1;
      if (got == pick) begin
        assert (m_data == kept);
        cover (pick == 5);
      end
    end
  end

  always_comb begin
    assert (inside <= 2);
    if (inside == 0) assert (!m_valid);
    cover (inside == 2);
  end
endmodule
