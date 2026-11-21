// Async FIFO with Gray-code pointers and two-flop synchronizers, after Cummings (SNUG 2002); reads are first-word-fall-through.
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
  logic [A:0] w_bin, w_gray, r_bin, r_gray, r_gray_w1, r_gray_w2, w_gray_r1, w_gray_r2;

  wire [A:0] w_bin_next  = w_bin + (A+1)'(w_en && !w_full);
  wire [A:0] w_gray_next = (w_bin_next >> 1) ^ w_bin_next;
  wire [A:0] r_bin_next  = r_bin + (A+1)'(r_en && !r_empty);
  wire [A:0] r_gray_next = (r_bin_next >> 1) ^ r_bin_next;

  always_ff @(posedge w_clk or negedge w_rst_n)
    if (!w_rst_n) {w_bin, w_gray, r_gray_w1, r_gray_w2, w_full} <= '0;
    else begin
      {w_bin, w_gray} <= {w_bin_next, w_gray_next};
      {r_gray_w2, r_gray_w1} <= {r_gray_w1, r_gray};
      w_full <= w_gray_next == {~r_gray_w2[A:A-1], r_gray_w2[A-2:0]};
    end

  always_ff @(posedge w_clk)
    if (w_en & ~w_full) mem[w_bin[A-1:0]] <= w_data;

  always_ff @(posedge r_clk or negedge r_rst_n)
    if (!r_rst_n) begin
      {r_bin, r_gray, w_gray_r1, w_gray_r2} <= '0;
      r_empty <= 1'b1;
    end else begin
      {r_bin, r_gray} <= {r_bin_next, r_gray_next};
      {w_gray_r2, w_gray_r1} <= {w_gray_r1, w_gray};
      r_empty <= r_gray_next == w_gray_r2;
    end

  assign r_data = mem[r_bin[A-1:0]];
endmodule
