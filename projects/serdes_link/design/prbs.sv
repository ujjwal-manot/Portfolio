// Parameterized PRBS7 (x^7 + x^6 + 1) and PRBS31 (x^31 + x^28 + 1) generator and self-synchronizing error checker for projects/serdes_link.
module prbs #(
  parameter int ORDER = 7
) (
  input  logic clk,
  input  logic rst_n,
  input  logic en,
  input  logic rx_bit,
  output logic tx_bit,
  output logic err_pulse
);
  localparam int TAP = (ORDER == 31) ? 27 : 5;
  logic [ORDER-1:0] tx_lfsr, rx_lfsr;
  logic tx_fb, rx_pred;

  assign tx_fb   = tx_lfsr[ORDER-1] ^ tx_lfsr[TAP];
  assign tx_bit  = tx_lfsr[ORDER-1];
  assign rx_pred = rx_lfsr[ORDER-1] ^ rx_lfsr[TAP];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      tx_lfsr   <= {ORDER{1'b1}};
      rx_lfsr   <= {ORDER{1'b1}};
      err_pulse <= 1'b0;
    end else if (en) begin
      tx_lfsr   <= {tx_lfsr[ORDER-2:0], tx_fb};
      err_pulse <= (rx_bit != rx_pred);
      rx_lfsr   <= {rx_lfsr[ORDER-2:0], rx_bit};
    end
  end
endmodule
