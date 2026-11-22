// Mixed-signal co-simulation harness joining rn_bandgap_ldo, rn_opamp_adc, rn_dldo_rail, and whole_chip_top with Verilator/cocotb-compatible microvolt and microamp boundary ports.
module whole_chip_cosim_top (
  input  logic         clk_adc,
  input  logic         clk_sys,
  input  logic         rst_ext_n,
  input  logic         ldo_en,
  input  logic [31:0]  vin_3v3_uv,
  input  logic [31:0]  v_sensor_uv,
  input  logic [31:0]  i_analog_ua,
  input  logic [31:0]  i_load_step_ua,
  output logic [31:0]  vref_bg_uv,
  output logic [31:0]  vdd_ana_uv,
  output logic [31:0]  v_amp_uv,
  output logic [31:0]  vdd_cpu_uv,
  output logic         por_ok,
  output logic         chip_rst_n,
  output logic         comp_out,
  output logic         dldo_lo,
  output logic         dldo_hi,
  output logic         dldo_far_lo,
  output logic         dldo_far_hi,
  output logic         droop_alert,
  output logic         adc_samp,
  output logic         adc_comp_clk,
  output logic [7:0]   adc_dac,
  output logic         adc_overflow,
  output logic [1:0]   dvfs_state,
  output logic [31:0]  fir_last,
  output logic [31:0]  peak_last,
  output logic         cpu_sleep,
  output logic [127:0] dldo_on
);
  real vdd_3v3, v_sensor, i_analog_a, i_load_step_a;
  real vref_bg, vdd_ana, v_amp, v_held, v_top, vdd_cpu, v_fb;

  assign vdd_3v3       = $itor(vin_3v3_uv) * 1.0e-6;
  assign v_sensor      = $itor(v_sensor_uv) * 1.0e-6;
  assign i_analog_a    = $itor(i_analog_ua) * 1.0e-6;
  assign i_load_step_a = $itor(i_load_step_ua) * 1.0e-6;
  assign chip_rst_n    = rst_ext_n & por_ok;

  assign vref_bg_uv = $rtoi(vref_bg * 1.0e6);
  assign vdd_ana_uv = $rtoi(vdd_ana * 1.0e6);
  assign v_amp_uv   = $rtoi(v_amp * 1.0e6);
  assign vdd_cpu_uv = $rtoi(vdd_cpu * 1.0e6);

  rn_bandgap_ldo u_bg_ldo (
    .clk(clk_sys),
    .en(ldo_en),
    .vdd_3v3(vdd_3v3),
    .i_load_a(i_analog_a),
    .vref_bg(vref_bg),
    .vdd_ana(vdd_ana),
    .por_ok(por_ok)
  );

  rn_opamp_adc u_opamp_adc (
    .rst_n(chip_rst_n),
    .adc_samp(adc_samp),
    .adc_comp_clk(adc_comp_clk),
    .adc_dac(adc_dac),
    .v_sensor(v_sensor),
    .vdd_ana(vdd_ana),
    .v_amp(v_amp),
    .v_held(v_held),
    .v_top(v_top),
    .comp_out(comp_out)
  );

  rn_dldo_rail u_dldo_rail (
    .clk_sys(clk_sys),
    .rst_n(chip_rst_n),
    .dldo_on(dldo_on),
    .dvfs_state(dvfs_state),
    .cpu_sleep(cpu_sleep),
    .vdd_3v3(vdd_3v3),
    .vref_bg(vref_bg),
    .i_load_step_a(i_load_step_a),
    .vdd_cpu(vdd_cpu),
    .v_fb(v_fb),
    .lo(dldo_lo),
    .hi(dldo_hi),
    .far_lo(dldo_far_lo),
    .far_hi(dldo_far_hi),
    .droop_alert(droop_alert)
  );

  whole_chip_top u_chip (
    .rst_n(chip_rst_n),
    .clk_adc(clk_adc),
    .clk_sys(clk_sys),
    .comp_out(comp_out),
    .dldo_lo(dldo_lo),
    .dldo_hi(dldo_hi),
    .dldo_far_lo(dldo_far_lo),
    .dldo_far_hi(dldo_far_hi),
    .droop_alert(droop_alert),
    .adc_samp(adc_samp),
    .adc_comp_clk(adc_comp_clk),
    .adc_dac(adc_dac),
    .adc_overflow(adc_overflow),
    .dvfs_state(dvfs_state),
    .fir_last(fir_last),
    .peak_last(peak_last),
    .cpu_sleep(cpu_sleep),
    .dldo_on(dldo_on)
  );
endmodule
