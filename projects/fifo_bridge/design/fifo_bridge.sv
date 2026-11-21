// Moves an 8-bit AXI-Stream with tlast from s_clk to m_clk: async_fifo across the clocks, skid_buffer on the output.
module fifo_bridge #(
  parameter int DEPTH_LOG2 = 4
) (
  input  logic       s_clk, s_rst_n,
  input  logic       s_tvalid,
  output logic       s_tready,
  input  logic [7:0] s_tdata,
  input  logic       s_tlast,
  input  logic       m_clk, m_rst_n,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast
);
  logic       full, empty, take;
  logic [8:0] fifo_out;

  assign s_tready = !full;

  async_fifo #(.WIDTH(9), .DEPTH_LOG2(DEPTH_LOG2)) fifo (
    .w_clk(s_clk), .w_rst_n(s_rst_n), .w_en(s_tvalid), .w_data({s_tlast, s_tdata}), .w_full(full),
    .r_clk(m_clk), .r_rst_n(m_rst_n), .r_en(take), .r_data(fifo_out), .r_empty(empty)
  );

  skid_buffer #(.WIDTH(9)) out (
    .clk(m_clk), .rst_n(m_rst_n),
    .s_valid(!empty), .s_ready(take), .s_data(fifo_out),
    .m_valid(m_tvalid), .m_ready(m_tready), .m_data({m_tlast, m_tdata})
  );
endmodule
