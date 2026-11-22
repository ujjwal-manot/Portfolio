// Alexander bang-bang clock and data recovery digital loop filter driving a 6-bit wrapping phase interpolator code for projects/serdes_link.
module bb_cdr #(
  parameter int PI_BITS = 6,
  parameter int KP = 1,
  parameter int KI_SHIFT = 4
) (
  input  logic               clk,
  input  logic               rst_n,
  input  logic               en,
  input  logic               d_prev,
  input  logic               edge_mid,
  input  logic               d_curr,
  output logic [PI_BITS-1:0] pi_code,
  output logic signed [15:0] freq_acc
);
  logic early, late;
  logic signed [15:0] vote, freq_next, phase_acc, phase_next;

  assign early = (d_prev != d_curr) && (edge_mid == d_curr);
  assign late  = (d_prev != d_curr) && (edge_mid == d_prev);
  assign vote  = late ? 16'sd1 : (early ? -16'sd1 : 16'sd0);

  assign freq_next  = freq_acc + vote;
  assign phase_next = phase_acc + (vote * KP) + (freq_next >>> KI_SHIFT);
  assign pi_code    = phase_acc[PI_BITS-1:0];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      freq_acc  <= 16'sd0;
      phase_acc <= 16'sd0;
    end else if (en) begin
      freq_acc  <= freq_next;
      phase_acc <= phase_next;
    end
  end
endmodule
