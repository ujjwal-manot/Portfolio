// Two-flop synchronizer; with METASTABLE defined (Icarus), a bit that changed in the 10 ns before the edge (half the fastest clock period, so one source change at most) randomly lands one cycle late.
module sync2 #(
  parameter int WIDTH = 1
) (
  input  logic             clk, rst_n,
  input  logic [WIDTH-1:0] d,
  output logic [WIDTH-1:0] q
);
  logic [WIDTH-1:0] meta;
`ifdef METASTABLE
  logic [WIDTH-1:0] late;
  int late_bits = 0;
  realtime changed [WIDTH];
  for (genvar i = 0; i < WIDTH; i++) begin : watch
    initial changed[i] = -1e9;
    always @(d[i]) changed[i] = $realtime;
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) {q, meta} <= '0;
    else begin
      for (int i = 0; i < WIDTH; i++) late[i] = $realtime - changed[i] < 10.0 && $urandom % 2;
      late_bits += $countones(late);
      {q, meta} <= {meta, d & ~late | meta & late};
    end
`else
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {q, meta} <= '0;
    else {q, meta} <= {meta, d};
`endif
endmodule
