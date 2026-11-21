// Two-register skid buffer: full throughput, and s_ready comes straight from a flop so no combinational path crosses it.
module skid_buffer #(
  parameter int WIDTH = 9
) (
  input  logic             clk, rst_n,
  input  logic             s_valid,
  output logic             s_ready,
  input  logic [WIDTH-1:0] s_data,
  output logic             m_valid,
  input  logic             m_ready,
  output logic [WIDTH-1:0] m_data
);
  logic             skid_valid;
  logic [WIDTH-1:0] skid;

  assign s_ready = !skid_valid;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {m_valid, skid_valid} <= '0;
    else if (m_ready || !m_valid) begin
      m_valid    <= skid_valid || s_valid;
      skid_valid <= 1'b0;
    end else if (s_valid && s_ready) skid_valid <= 1'b1;

  always_ff @(posedge clk) begin
    if (m_ready || !m_valid) m_data <= skid_valid ? skid : s_data;
    if (s_ready) skid <= s_data;
  end
endmodule
