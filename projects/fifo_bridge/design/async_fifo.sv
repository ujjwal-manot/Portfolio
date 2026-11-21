// Async FIFO with Gray-code pointers crossing through sync2, after Cummings (SNUG 2002); reads are first-word-fall-through, full reads 1 during reset, and full and empty are kept inverted (room, ready) because IHP has no set flops; under FORMAL it proves each Gray pointer moves one bit at a time.
module async_fifo #(
  parameter int WIDTH = 9,
  parameter int DEPTH_LOG2 = 4
) (
  input  logic             w_clk, w_rst_n, w_en,
  input  logic [WIDTH-1:0] w_data,
  output logic             w_full,
  input  logic             r_clk, r_rst_n, r_en,
  output logic [WIDTH-1:0] r_data,
  output logic             r_empty
);
  localparam int A = DEPTH_LOG2;

  logic [WIDTH-1:0] mem [2**A];
  logic [A:0] w_bin, w_gray, r_bin, r_gray, r_gray_w, w_gray_r;
  logic       w_room, r_ready;

  assign w_full  = !w_room;
  assign r_empty = !r_ready;

  wire [A:0] w_bin_next  = w_bin + (A+1)'(w_en && !w_full);
  wire [A:0] w_gray_next = (w_bin_next >> 1) ^ w_bin_next;
  wire [A:0] r_bin_next  = r_bin + (A+1)'(r_en && !r_empty);
  wire [A:0] r_gray_next = (r_bin_next >> 1) ^ r_bin_next;

  sync2 #(.WIDTH(A+1)) r_to_w (.clk(w_clk), .rst_n(w_rst_n), .d(r_gray), .q(r_gray_w));
  sync2 #(.WIDTH(A+1)) w_to_r (.clk(r_clk), .rst_n(r_rst_n), .d(w_gray), .q(w_gray_r));

  always_ff @(posedge w_clk or negedge w_rst_n)
    if (!w_rst_n) {w_bin, w_gray, w_room} <= '0;
    else {w_bin, w_gray, w_room} <= {w_bin_next, w_gray_next, w_gray_next != {~r_gray_w[A:A-1], r_gray_w[A-2:0]}};

  always_ff @(posedge w_clk)
    if (w_en & ~w_full) mem[w_bin[A-1:0]] <= w_data;

  always_ff @(posedge r_clk or negedge r_rst_n)
    if (!r_rst_n) {r_bin, r_gray, r_ready} <= '0;
    else {r_bin, r_gray, r_ready} <= {r_bin_next, r_gray_next, r_gray_next != w_gray_r};

  assign r_data = mem[r_bin[A-1:0]];

`ifdef FORMAL
  logic [A:0] w_gray_was = '0, r_gray_was = '0;
  always_ff @(posedge w_clk) begin
    w_gray_was <= w_gray;
    assert ($countones(w_gray ^ w_gray_was) <= 1);
  end
  always_ff @(posedge r_clk) begin
    r_gray_was <= r_gray;
    assert ($countones(r_gray ^ r_gray_was) <= 1);
  end
`endif
endmodule
