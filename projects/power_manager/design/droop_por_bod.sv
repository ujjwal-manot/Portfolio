// Power-on reset, brown-out detector (800 mV trip with 40 mV hysteresis), and 16-tap delay-line droop detector calibrated to power_manager/results/speed.log (1.973x at 0.90 V, 1.305x at 1.00 V, 0.964x at 1.10 V, 0.806x at 1.20 V) that stretches clk_cpu during supply sags.
module droop_por_bod #(
  parameter int POR_CYCLES    = 16,
  parameter int POR_RISE_MV   = 1160,
  parameter int BOD_TRIP_MV   = 800,
  parameter int BOD_HYST_MV   = 40,
  parameter int DELAY_TAPS    = 16,
  parameter int DROOP_HYST_MV = 25
) (
  input  logic        clk_sys,
  input  logic        rst_ext_n,
  input  logic        bg_ok,
  input  logic [1:0]  dvfs_state,
  input  logic [11:0] vdd_cpu_mv,
  input  logic [4:0]  delay_taps_reached,
  output logic        por_n,
  output logic        bod_alert,
  output logic        droop_alert,
  output logic        clk_cpu_en,
  output logic        clk_cpu,
  output logic        sys_rst_n
);
  logic [$clog2(POR_CYCLES+1)-1:0] por_cnt;
  logic [11:0] droop_mv;
  logic [4:0]  min_taps;
  logic        sag_now, rec_now;

  always_comb begin
    case (dvfs_state)
      2'd0: begin droop_mv = 12'd855;  min_taps = 5'd7;  end
      2'd1: begin droop_mv = 12'd950;  min_taps = 5'd9;  end
      2'd2: begin droop_mv = 12'd1045; min_taps = 5'd11; end
      default: begin droop_mv = 12'd1140; min_taps = 5'd13; end
    endcase
    sag_now = (vdd_cpu_mv < droop_mv) || (delay_taps_reached < min_taps);
    rec_now = (vdd_cpu_mv >= (droop_mv + 12'(DROOP_HYST_MV))) && (delay_taps_reached >= min_taps);
  end

  always_ff @(posedge clk_sys or negedge rst_ext_n) begin
    if (!rst_ext_n) begin
      por_cnt   <= '0;
      por_n     <= 1'b0;
      bod_alert <= 1'b0;
    end else if (!bg_ok) begin
      por_cnt   <= '0;
      por_n     <= 1'b0;
      bod_alert <= 1'b0;
    end else if (!por_n) begin
      if (vdd_cpu_mv >= 12'(POR_RISE_MV)) begin
        if (por_cnt < ($clog2(POR_CYCLES+1))'(POR_CYCLES)) por_cnt <= por_cnt + 1'b1;
        else por_n <= 1'b1;
      end else begin
        por_cnt <= '0;
      end
    end else begin
      if (vdd_cpu_mv < 12'(BOD_TRIP_MV)) bod_alert <= 1'b1;
      else if (vdd_cpu_mv >= 12'(BOD_TRIP_MV + BOD_HYST_MV)) bod_alert <= 1'b0;
    end
  end

  assign sys_rst_n = por_n && !bod_alert;

  always_ff @(negedge clk_sys or negedge rst_ext_n) begin
    if (!rst_ext_n) droop_alert <= 1'b1;
    else if (sag_now) droop_alert <= 1'b1;
    else if (rec_now) droop_alert <= 1'b0;
  end

  always_latch begin
    if (!clk_sys) clk_cpu_en = sys_rst_n && !droop_alert;
  end
  assign clk_cpu = clk_sys & clk_cpu_en;
endmodule
