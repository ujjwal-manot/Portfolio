// Digital LDO controller, proportional plus integral: on every clock it reads four clocked comparators around the setpoint, a fine window (lo: the rail is below it, hi: above it) and a wider coarse one (far_lo, far_hi); the count (the integral) moves by BIG units beyond the coarse window, by one unit between the two and not at all inside the fine window, never past 0 or N, and on top of the count PB more units are turned on (or off) beyond the coarse window and P more between the two, proportional kicks that damp the rail, whose voltage is itself the integral of the units' current against the load's; the coarse window counts only when one side of it trips, so both coarse comparators asserting at once (a fault or a metastable pair, never a real rail) moves nothing; the units are driven as a registered thermometer code, so a unit never glitches on.
module dldo_ctrl #(
  parameter int N = 128,
  parameter int BIG = 8,
  parameter int P = 1,
  parameter int PB = 8
) (
  input  logic         clk, rst_n,
  input  logic         lo, hi, far_lo, far_hi,
  output logic [N-1:0] on,
  output logic [$clog2(N+1)-1:0] count, drive
);
  int next_count, next_drive;
  wire up = lo && !hi, down = hi && !lo;
  wire far_up = far_lo && !far_hi, far_dn = far_hi && !far_lo;

  always_comb begin
    next_count = int'(count);
    if (far_up) next_count = next_count + BIG;
    else if (far_dn) next_count = next_count - BIG;
    else if (up) next_count = next_count + 1;
    else if (down) next_count = next_count - 1;
    next_count = next_count > N ? N : next_count < 0 ? 0 : next_count;
    next_drive = next_count + (far_up ? PB : far_dn ? -PB : up ? P : down ? -P : 0);
    next_drive = next_drive > N ? N : next_drive < 0 ? 0 : next_drive;
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {count, drive, on} <= '0;
    else begin
      count <= ($clog2(N+1))'(next_count);
      drive <= ($clog2(N+1))'(next_drive);
      for (int i = 0; i < N; i++) on[i] <= i < next_drive;
    end
endmodule
