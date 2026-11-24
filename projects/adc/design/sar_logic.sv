// SAR control for the 8-bit ADC: each sample takes 10 clk cycles (2 sampling, 8 bit trials MSB first); the comparator is clocked in the low half of each trial cycle and comp_out high means the input is above the DAC level, so the bit stays; finished codes go out on AXI4-Stream with m_tlast on every 64th delivered sample, and a code that finds the previous one still waiting is dropped and sets the sticky overflow flag.
module sar_logic (
  input  logic       clk, rst_n, comp_out,
  output logic       samp, comp_clk,
  output logic [7:0] dac,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast,
  output logic       overflow
);
  logic [3:0] cycle;
  logic [7:0] trial;
  logic [5:0] count;
  logic       busy;
  wire        done = cycle == 0 && busy;
  wire [7:0]  code = comp_out ? dac : dac & ~trial;

  assign samp = cycle < 2;
  assign comp_clk = !samp && !clk;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {cycle, trial, dac, busy} <= '0;
    else begin
      cycle <= cycle == 9 ? 4'd0 : cycle + 4'd1;
      busy  <= busy || cycle == 9;
      if (cycle == 1) {dac, trial} <= {8'h80, 8'h80};
      else if (cycle >= 2) {dac, trial} <= {code | trial >> 1, trial >> 1};
    end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {m_tvalid, m_tdata, m_tlast, count, overflow} <= '0;
    else begin
      if (m_tvalid && m_tready) m_tvalid <= 1'b0;
      if (done && m_tvalid && !m_tready) overflow <= 1'b1;
      else if (done) begin
        {m_tvalid, m_tdata, m_tlast} <= {1'b1, dac, count == 6'd63};
        count <= count + 6'd1;
      end
    end
endmodule
