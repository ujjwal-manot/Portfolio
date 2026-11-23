// Clock stretch on droop: the droop detector's capture latches (q, tap k reached when it equals 1 for even k and 0 for odd k) give a code, the number of taps reached (a count, so a bubble moves it by one, not by half the line); a code under threshold means vdd_cpu has sagged, and from then until HOLD clocks after the last low code every other cpu clock edge is swallowed, so the cpu's period doubles; the enable changes only on the falling edge, while clk is low, so clk_cpu = clk & en never gives a runt pulse; with enable low the cpu clock is never touched.
module clock_stretch #(
  parameter int NT = 64,
  parameter int HOLD = 2
) (
  input  logic          clk, rst_n, enable,
  input  logic [NT:1]   q,
  input  logic [7:0]    threshold,
  output logic [7:0]    code,
  output logic          droop, en,
  output logic          clk_cpu
);
  logic [$clog2(HOLD+1)-1:0] hold;
  wire stretching = enable && (droop || hold != 0);

  always_comb begin
    code = '0;
    for (int k = 1; k <= NT; k++) code = code + 8'(q[k] == (k % 2 == 0));
  end
  assign droop = code < threshold;

  always_ff @(negedge clk or negedge rst_n)
    if (!rst_n) begin
      hold <= '0;
      en <= 1'b1;
    end else begin
      hold <= droop ? ($clog2(HOLD+1))'(HOLD) : hold != 0 ? hold - 1'b1 : hold;
      en <= stretching ? !en : 1'b1;
    end

  assign clk_cpu = clk & en;
endmodule
