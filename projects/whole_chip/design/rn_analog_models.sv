// Real-number behavioral SystemVerilog models for whole_chip mixed-signal co-simulation: rn_bandgap_ldo (chip.md vref 1.206 V, floor >= 1.16 V, thin-oxide <= 1.32 V, ldo_sizes.inc 100 pF MIM + 110 uA bleed), rn_opamp_adc (review_opamp.log A0 77.08 dB = 7145, corners.log worst 66.14 dB / 0.06189..1.031 V at 1.16 V / 0.9506 V at 1.08 V / 224.7 uA, mc.log Vos sigma 2.666 mV, cap_dac 256x7.95 fF, decide.log 0.800 ns max), and rn_dldo_rail (dldo_sizes.inc 128 PMOS units 115..335 uA + 2 nF rail + 52 kOhm divider, make_loop.py ladder taps 0.570/0.594/0.606/0.630 V, cpu power.log 7.5 mA at 1.2 V, power_manager/results/speed.log slow-corner delay ratios 1.973x at 0.90 V, 1.305x at 1.00 V, 0.964x at 1.10 V, 0.806x at 1.20 V).
module rn_bandgap_ldo #(
  parameter real VREF_NOM_V     = 1.206,
  parameter real VDD_MIN_OK_V   = 1.160,
  parameter real VDD_BROWNOUT_V = 1.120,
  parameter real VDD_MAX_OX_V   = 1.320,
  parameter real VIN_UVLO_V     = 2.500,
  parameter real R_LOAD_REG     = 2.0,
  parameter real LINE_REG_VPV   = 0.005,
  parameter real R_TRANS_OHM    = 40.0,
  parameter real ALPHA_BG       = 0.0645,
  parameter real ALPHA_LOOP     = 0.2835,
  parameter real ALPHA_OUT      = 0.1813
) (
  input  logic clk,
  input  logic en,
  input  real  vdd_3v3,
  input  real  i_load_a,
  output real  vref_bg,
  output real  vdd_ana,
  output logic por_ok
);
  real        i_pass_track;
  real        v_bg_next, i_track_next, v_target, v_raw, v_ana_next;
  logic [1:0] ok_cnt;

  always_comb begin
    v_bg_next    = vref_bg + ALPHA_BG * (VREF_NOM_V - vref_bg);
    i_track_next = i_pass_track + ALPHA_LOOP * (i_load_a - i_pass_track);
    v_target     = v_bg_next - R_LOAD_REG * i_load_a + LINE_REG_VPV * (vdd_3v3 - 3.3);
    v_raw        = v_target - (i_load_a - i_track_next) * R_TRANS_OHM;
    v_ana_next   = vdd_ana + ALPHA_OUT * (v_raw - vdd_ana);
    if (v_ana_next < 0.0) v_ana_next = 0.0;
    if (v_ana_next > VDD_MAX_OX_V) v_ana_next = VDD_MAX_OX_V;
    if (v_ana_next > vdd_3v3) v_ana_next = vdd_3v3;
  end

  always @(posedge clk) begin
    if (!en || vdd_3v3 < VIN_UVLO_V) begin
      vref_bg      <= 0.0;
      i_pass_track <= 0.0;
      vdd_ana      <= 0.0;
    end else begin
      vref_bg      <= v_bg_next;
      i_pass_track <= i_track_next;
      vdd_ana      <= v_ana_next;
    end
  end

  always_ff @(posedge clk) begin
    if (!en || vdd_3v3 < VIN_UVLO_V || vdd_ana < VDD_BROWNOUT_V) begin
      ok_cnt <= 2'd0;
      por_ok <= 1'b0;
    end else if (vdd_ana >= VDD_MIN_OK_V) begin
      if (ok_cnt < 2'd2) ok_cnt <= ok_cnt + 2'd1;
      else por_ok <= 1'b1;
    end
  end
endmodule

module rn_opamp_adc #(
  parameter real VCM_V        = 0.600,
  parameter real VREF_LO_V    = 0.200,
  parameter real VREF_HI_V    = 1.000,
  parameter real A0_LIN       = 7145.0,
  parameter real V_OPAMP_OS_V = 0.0,
  parameter real V_COMP_OS_V  = 0.0,
  parameter real OUT_LOW_V    = 0.06189,
  parameter real OUT_HIGH_V   = 1.031,
  parameter real PMOS_HEAD_V  = 0.1294
) (
  input  logic       rst_n,
  input  logic       adc_samp,
  input  logic       adc_comp_clk,
  input  logic [7:0] adc_dac,
  input  real        v_sensor,
  input  real        vdd_ana,
  output real        v_amp,
  output real        v_held,
  output real        v_top,
  output logic       comp_out
);
  real cl_gain, v_hi_lim, v_raw_amp, v_dac;

  always_comb begin
    cl_gain   = 1.0 / (1.0 + 2.0 / A0_LIN);
    v_raw_amp = VCM_V - (v_sensor - VCM_V) * cl_gain + 2.0 * V_OPAMP_OS_V;
    v_hi_lim  = (vdd_ana >= 1.160) ? OUT_HIGH_V : (vdd_ana - PMOS_HEAD_V);
    if (v_hi_lim < OUT_LOW_V) v_hi_lim = OUT_LOW_V;
    if (v_raw_amp < OUT_LOW_V) v_amp = OUT_LOW_V;
    else if (v_raw_amp > v_hi_lim) v_amp = v_hi_lim;
    else v_amp = v_raw_amp;

    v_dac = VREF_LO_V + ($itor({24'd0, adc_dac}) / 256.0) * (VREF_HI_V - VREF_LO_V);
    v_top = adc_samp ? VCM_V : (VCM_V + (v_dac - v_held));
  end

  always @(negedge adc_samp or negedge rst_n) begin
    if (!rst_n) v_held <= VCM_V;
    else v_held <= v_amp;
  end

  always_ff @(posedge adc_comp_clk or negedge rst_n) begin
    if (!rst_n) comp_out <= 1'b0;
    else comp_out <= ((VCM_V + V_COMP_OS_V) > v_top);
  end
endmodule

module rn_dldo_rail #(
  parameter int  N_UNITS      = 128,
  parameter real C_RAIL_F     = 2.0e-9,
  parameter real DT_SYS_S     = 20.0e-9,
  parameter real I_UNIT_NOM_A = 200.0e-6,
  parameter real R_DIV_OHM    = 52.0e3,
  parameter real I_CPU_ACT_A  = 7.5e-3,
  parameter real I_CPU_SLP_A  = 0.5e-3,
  parameter real V_TAP_FAR_LO = 0.570,
  parameter real V_TAP_LO     = 0.594,
  parameter real V_TAP_HI     = 0.606,
  parameter real V_TAP_FAR_HI = 0.630,
  parameter real V_DROOP_REL  = 0.585
) (
  input  logic               clk_sys,
  input  logic               rst_n,
  input  logic [N_UNITS-1:0] dldo_on,
  input  logic [1:0]         dvfs_state,
  input  logic               cpu_sleep,
  input  real                vdd_3v3,
  input  real                vref_bg,
  input  real                i_load_step_a,
  output real                vdd_cpu,
  output real                v_fb,
  output logic               lo,
  output logic               hi,
  output logic               far_lo,
  output logic               far_hi,
  output logic               droop_alert
);
  real    v_target, ref_scale, v_head, i_pmos, i_cpu, i_div, i_load, v_cpu_next;
  integer n_on;

  always_comb begin
    case (dvfs_state)
      2'd0: v_target = 0.90;
      2'd1: v_target = 1.00;
      2'd2: v_target = 1.10;
      default: v_target = 1.20;
    endcase
    v_fb      = vdd_cpu * (0.600 / v_target);
    ref_scale = (vref_bg > 0.1) ? (vref_bg / 1.206) : 1.0;
    n_on      = 0;
    for (int i = 0; i < N_UNITS; i++) begin
      if (dldo_on[i]) n_on = n_on + 1;
    end
    v_head     = (vdd_3v3 > vdd_cpu) ? ((vdd_3v3 - vdd_cpu) / 2.3) : 0.0;
    i_pmos     = $itor(n_on) * I_UNIT_NOM_A * v_head;
    i_cpu      = (cpu_sleep || droop_alert) ? I_CPU_SLP_A : (I_CPU_ACT_A * (vdd_cpu / 1.20));
    i_div      = vdd_cpu / R_DIV_OHM;
    i_load     = i_cpu + i_div + i_load_step_a;
    v_cpu_next = vdd_cpu + ((i_pmos - i_load) * DT_SYS_S) / C_RAIL_F;
    if (v_cpu_next < 0.0) v_cpu_next = 0.0;
    if (v_cpu_next > vdd_3v3) v_cpu_next = vdd_3v3;
  end

  always @(posedge clk_sys or negedge rst_n) begin
    if (!rst_n) vdd_cpu <= 0.0;
    else vdd_cpu <= v_cpu_next;
  end

  always_ff @(negedge clk_sys or negedge rst_n) begin
    if (!rst_n) begin
      lo          <= 1'b0;
      hi          <= 1'b0;
      far_lo      <= 1'b0;
      far_hi      <= 1'b0;
      droop_alert <= 1'b1;
    end else begin
      lo     <= (v_fb < (V_TAP_LO * ref_scale));
      hi     <= (v_fb > (V_TAP_HI * ref_scale));
      far_lo <= (v_fb < (V_TAP_FAR_LO * ref_scale));
      far_hi <= (v_fb > (V_TAP_FAR_HI * ref_scale));
      if (v_fb < (V_TAP_FAR_LO * ref_scale)) droop_alert <= 1'b1;
      else if (v_fb >= (V_DROOP_REL * ref_scale)) droop_alert <= 1'b0;
    end
  end
endmodule
