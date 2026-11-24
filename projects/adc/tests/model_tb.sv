// Runs adc_model with the same clock (10 MHz, first rise at 50 ns) and reset release (250.5 ns) as tests/convert.cir: +stim=tone gives vin = 0.6 V + amp sin(2 pi k / n_fft x 1 MHz x t) (+amp=, +k=, +nfft=), set at every clk rise so each sample takes the tone at its sampling edge, +stim=ramp holds each value of the +levels= file through one sample after calibration, moving on at the falling clk after it; it writes the trim code calibration settled on and then the first +n= delivered codes, one per line, to +out=.
`timescale 1ns / 1ps
module model_tb;
  logic clk = 1'b0, rst_n = 1'b0;
  real vin = 0.6, amp, steps [$];
  logic m_tvalid, m_tlast, overflow, cal;
  logic [7:0] m_tdata;
  logic [6:0] trim;
  integer n, k, nfft, fd, out, m = 0, got = 0;
  real value;
  string stim, levels, path;

  adc_model dut (.clk, .rst_n, .m_tready(1'b1), .vin, .m_tvalid, .m_tdata, .m_tlast, .overflow, .cal, .trim);

  initial begin
    if (!$value$plusargs("stim=%s", stim) || !$value$plusargs("n=%d", n) || !$value$plusargs("out=%s", path)) $fatal(1, "model_tb: needs +stim= +n= +out=");
    if (stim == "tone" && !($value$plusargs("amp=%f", amp) && $value$plusargs("k=%d", k) && $value$plusargs("nfft=%d", nfft))) $fatal(1, "model_tb: a tone needs +amp= +k= +nfft=");
    if (stim == "ramp") begin
      if (!$value$plusargs("levels=%s", levels)) $fatal(1, "model_tb: a ramp needs +levels=");
      fd = $fopen(levels, "r");
      while ($fscanf(fd, "%f", value) == 1) steps.push_back(value);
      $fclose(fd);
      vin = steps[0];
    end
    out = $fopen(path, "w");
    #50;
    forever begin clk = 1'b1; #50; clk = 1'b0; #50; end
  end

  initial #250.5 rst_n = 1'b1;

  logic sampled = 1'b0;

  always @(posedge clk) if (stim == "tone") vin = 0.6 + amp * $sin(2.0 * 3.14159265358979 * k * 1.0e6 / nfft * $realtime * 1.0e-9);

  always @(negedge dut.samp) if (stim == "ramp" && !cal) sampled = 1'b1;

  always @(negedge clk) if (sampled) begin
    sampled = 1'b0;
    m = m + 1;
    if (m < steps.size()) vin = steps[m];
  end

  always @(posedge clk) if (m_tvalid) begin
    if (got == 0) $fdisplay(out, "trim %0d", trim);
    $fdisplay(out, "%0d", m_tdata);
    got = got + 1;
    if (got == n) begin
      $fclose(out);
      $finish;
    end
  end
endmodule
