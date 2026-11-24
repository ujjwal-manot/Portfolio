// SAR control for the 8-bit ADC: each sample takes 10 clk cycles (2 sampling, 8 bit trials MSB first); the comparator is clocked in the low half of each trial cycle and comp_out high means the input is above the DAC level, so the bit stays; after reset 8 calibration frames run with cal high, where the DAC samples and holds its own 0x80 level instead of vin, so the comparator sees only its offset, and a 7-bit SAR search on the top-plate trim code in the first 7 trials of each frame (comp_out high keeps the bit, raising the plate) gives one estimate; the rounded mean of the 8 estimates is the trim held from then on (an out-of-range offset ends at 0 or 127), and no code is delivered while calibrating; finished codes go out on AXI4-Stream with m_tlast on every 64th delivered sample, and a code that finds the previous one still waiting is dropped and sets the sticky overflow flag.
module sar_logic (
  input  logic       clk, rst_n, comp_out,
  output logic       samp, comp_clk,
  output logic [7:0] dac,
  output logic       cal,
  output logic [6:0] trim,
  output logic       m_tvalid,
  input  logic       m_tready,
  output logic [7:0] m_tdata,
  output logic       m_tlast,
  output logic       overflow
);
  logic [3:0] cycle, frames;
  logic [7:0] trial, code_r;
  logic [6:0] search, tbit, held;
  logic [9:0] sum;
  logic [5:0] count;
  logic       converted;
  wire        done = cycle == 0 && converted;
  wire [7:0]  code = comp_out ? code_r : code_r & ~trial;
  wire [9:0]  total = sum + {3'b0, search};

  assign samp = cycle < 2;
  assign comp_clk = !samp && !clk;
  assign dac = cal ? 8'h80 : code_r;
  assign trim = cal ? search : held;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {cycle, trial, code_r, converted} <= '0;
    else begin
      cycle <= cycle == 9 ? 4'd0 : cycle + 4'd1;
      converted <= cycle == 9 ? !cal : converted && cycle != 0;
      if (cycle == 1) {code_r, trial} <= {8'h80, 8'h80};
      else if (cycle >= 2) {code_r, trial} <= {code | trial >> 1, trial >> 1};
    end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      {search, tbit, held, sum, frames} <= '0;
      cal <= 1'b1;
    end else if (cal) begin
      if (cycle == 1) {search, tbit} <= {7'h40, 7'h40};
      else if (cycle >= 2 && tbit != 0) {search, tbit} <= {(comp_out ? search : search & ~tbit) | tbit >> 1, tbit >> 1};
      else if (cycle == 9) begin
        sum <= total;
        frames <= frames + 4'd1;
        if (frames == 4'd7) begin
          held <= 7'((total + 10'd4) >> 3);
          cal <= 1'b0;
        end
      end
    end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {m_tvalid, m_tdata, m_tlast, count, overflow} <= '0;
    else begin
      if (m_tvalid && m_tready) m_tvalid <= 1'b0;
      if (done && m_tvalid && !m_tready) overflow <= 1'b1;
      else if (done) begin
        {m_tvalid, m_tdata, m_tlast} <= {1'b1, code_r, count == 6'd63};
        count <= count + 6'd1;
      end
    end
endmodule
