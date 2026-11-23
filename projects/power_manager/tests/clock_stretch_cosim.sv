// The clock stretch logic as ngspice d_cosim sees it in the droop runs: every port is 8 bits or less so they keep their declared order (the detector's 64 latch outputs as eight bytes, q7 holding taps 64 down to 57 first, q0 holding taps 8 down to 1 last), the threshold is this wrapper's parameter default (vlnggen ignores -G overrides), and act, the enable as it stood at the last rising clk edge, tells the testbench's cpu load whether this cycle's clock edge reached the cpu.
module clock_stretch_cosim #(parameter int THRESHOLD = 0) (
  input  logic       clk, rst_n, enable,
  input  logic [7:0] q7, q6, q5, q4, q3, q2, q1, q0,
  output logic       en, clk_cpu, droop, act,
  output logic [7:0] code
);
  clock_stretch #(.NT(64), .HOLD(2)) stretch (.clk, .rst_n, .enable, .q({q7, q6, q5, q4, q3, q2, q1, q0}), .threshold(8'(THRESHOLD)), .code, .droop, .en, .clk_cpu);
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) act <= 1'b0;
    else act <= en;
endmodule
