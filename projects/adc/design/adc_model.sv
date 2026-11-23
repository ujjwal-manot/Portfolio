// Real-number model of the 8-bit SAR ADC for mixed-signal runs: the real sar_logic RTL drives a model front end whose numbers all come from transistor results through adc_model.py: at each falling samp it holds vin (or, while cal is high, the DAC's own level for its code, as the transistor DAC samples itself), and at each rising comp_clk the comparator keeps the bit when the held input minus the DAC level for the code minus the trim shift for the trim code plus the offset (offset_cal_v while calibrating, offset_v after) is above zero, every value in volts at the input; the table file (from the TABLE parameter, or +table= when empty) holds offset_v and offset_cal_v, then the 256 DAC levels, then the 128 trim shifts.
module adc_model #(parameter string TABLE = "") (
  input  logic       clk, rst_n, m_tready,
  input  real        vin,
  output logic       m_tvalid,
  output logic [7:0] m_tdata,
  output logic       m_tlast,
  output logic       overflow,
  output logic       cal,
  output logic [6:0] trim
);
  real level [256];
  real shift [128];
  real offset_v, offset_cal_v, held;
  logic samp, comp_clk, comp_out;
  logic [7:0] dac;
  string name;
  integer fd, got;

  sar_logic core (.clk, .rst_n, .comp_out, .samp, .comp_clk, .dac, .cal, .trim, .m_tvalid, .m_tready, .m_tdata, .m_tlast, .overflow);

  initial begin
    name = TABLE;
    if (name == "" && !$value$plusargs("table=%s", name)) $fatal(1, "adc_model: no table file");
    fd = $fopen(name, "r");
    if (fd == 0) $fatal(1, "adc_model: cannot open %s", name);
    got = $fscanf(fd, "%f %f", offset_v, offset_cal_v);
    for (int i = 0; i < 256; i++) got += $fscanf(fd, "%f", level[i]);
    for (int i = 0; i < 128; i++) got += $fscanf(fd, "%f", shift[i]);
    if (got != 2 + 256 + 128) $fatal(1, "adc_model: %s holds %0d of the 386 numbers", name, got);
    $fclose(fd);
    comp_out = 1'b0;
    held = 0.0;
  end

  always @(negedge samp) held = cal ? level[dac] : vin;

  always @(posedge comp_clk) comp_out <= held - level[dac] - shift[trim] + (cal ? offset_cal_v : offset_v) > 0.0;
endmodule
