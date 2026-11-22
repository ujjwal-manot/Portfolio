// Synthesizable 3-threshold PAM4 Gray-code slicer mapping signed W-bit equalizer samples into Gray dibits (00, 01, 11, 10) for projects/serdes_link.
module pam4_slicer #(
  parameter int W = 10,
  parameter logic signed [W-1:0] T_LOW  = -10'sd32,
  parameter logic signed [W-1:0] T_MID  =  10'sd0,
  parameter logic signed [W-1:0] T_HIGH =  10'sd32
) (
  input  logic                clk,
  input  logic                rst_n,
  input  logic                en,
  input  logic signed [W-1:0] sample_in,
  output logic [1:0]          sym_out
);
  logic [1:0] sym_next;

  always_comb begin
    if (sample_in < T_LOW)       sym_next = 2'b00;
    else if (sample_in < T_MID)  sym_next = 2'b01;
    else if (sample_in < T_HIGH) sym_next = 2'b11;
    else                         sym_next = 2'b10;
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sym_out <= 2'b00;
    end else if (en) begin
      sym_out <= sym_next;
    end
  end
endmodule
