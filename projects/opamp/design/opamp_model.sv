// Real-number model of the opamp in its inverting loop (Rin = Rf, inp at 0.6 V, 2.05 pF load): the output heads for mid + slope * (0.6 - vin), clamped to out_low..out_high, through a two-pole loop (integrator wu, second pole p2) whose integrator is slew-limited to slew_up and slew_down V/s; every constant comes from one corner's transistor measurements through helpers/opamp_model.py, and the model is stepped every 10 ps.
`timescale 1ps/1ps
module opamp_model #(parameter real mid = 0.6, slope = 1.0, out_low = 0.2, out_high = 1.0, wu = 1e8, p2 = 3e8, slew_up = 2e7, slew_down = 2e7)
  (input real vin, output real vout);
  localparam real dt = 10e-12;
  real target, y, dy;
  bit started = 0;
  always #10 begin
    target = mid + slope * (0.6 - vin);
    target = target > out_high ? out_high : target < out_low ? out_low : target;
    if (!started) begin
      y = target;
      vout = target;
      started = 1;
    end
    dy = wu * (target - vout) * dt;
    dy = dy > slew_up * dt ? slew_up * dt : dy < -slew_down * dt ? -slew_down * dt : dy;
    y = y + dy;
    vout = vout + (y - vout) * (1 - $exp(-p2 * dt));
  end
endmodule
