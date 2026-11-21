// Two-flop synchronizer; with METASTABLE defined (Icarus), a bit that changed 61.6 to 177.1 ps before the edge lands old or new at random, and one that changed later keeps its old value: the spread of the flip point of the extracted sg13g2_dfrbpq_1 over tt, ss and ff corners and both data edges, measured by make mtbf and checked against this file by mtbf/mtbf.py; under FORMAL any bit that changed since the last edge may land old or new, as the solver chooses, and a cover shows a changed bit really landing old.
module sync2 #(
  parameter int WIDTH = 1
) (
  input  logic             clk, rst_n,
  input  logic [WIDTH-1:0] d,
  output logic [WIDTH-1:0] q
);
  logic [WIDTH-1:0] meta;
`ifdef METASTABLE
  localparam real KEEP = 0.0616, TAKE = 0.1771;
  logic [WIDTH-1:0] late;
  int late_bits = 0;
  realtime age;
  realtime changed [WIDTH];
  for (genvar i = 0; i < WIDTH; i++) begin : watch
    initial changed[i] = -1e9;
    always @(d[i]) changed[i] = $realtime;
  end
  always @(posedge clk or negedge rst_n)
    if (!rst_n) {q, meta} <= '0;
    else begin
      for (int i = 0; i < WIDTH; i++) begin
        age = $realtime - changed[i];
        late[i] = age < KEEP || age < TAKE && $urandom % 2;
        late_bits += age >= KEEP && late[i];
      end
      {q, meta} <= {meta, d & ~late | meta & late};
    end
`elsif FORMAL
  logic [WIDTH-1:0] seen, changed, old;
  (* anyseq *) logic [WIDTH-1:0] pick;
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {q, meta, seen, changed, old} <= '0;
    else {q, meta, seen, changed, old} <= {meta, d & pick | seen & ~pick, d, d ^ seen, seen};
  always_comb if (rst_n) cover (|(changed & ~(meta ^ old)));
`else
  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) {q, meta} <= '0;
    else {q, meta} <= {meta, d};
`endif
endmodule
