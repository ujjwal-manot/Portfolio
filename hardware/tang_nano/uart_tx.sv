// Synthesizable 8N1 UART transmitter for the Tang Nano 20K (27 MHz default clock, 115200 baud) with busy handshake.
module uart_tx #(
  parameter int CLK_HZ = 27_000_000,
  parameter int BAUD   = 115_200
) (
  input  logic       clk,
  input  logic       rst_n,
  input  logic       tx_valid,
  input  logic [7:0] tx_data,
  output logic       tx_busy,
  output logic       tx_pin
);
  localparam int DIV = CLK_HZ / BAUD;
  logic [15:0] div_cnt;
  logic [3:0]  bit_cnt;
  logic [9:0]  shift_reg;

  assign tx_busy = (bit_cnt != 4'd0);
  assign tx_pin  = tx_busy ? shift_reg[0] : 1'b1;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      div_cnt   <= 16'd0;
      bit_cnt   <= 4'd0;
      shift_reg <= 10'h3ff;
    end else if (!tx_busy) begin
      if (tx_valid) begin
        shift_reg <= {1'b1, tx_data, 1'b0};
        bit_cnt   <= 4'd10;
        div_cnt   <= 16'd0;
      end
    end else if (div_cnt == 16'(DIV - 1)) begin
      div_cnt   <= 16'd0;
      shift_reg <= {1'b1, shift_reg[9:1]};
      bit_cnt   <= bit_cnt - 4'd1;
    end else begin
      div_cnt <= div_cnt + 16'd1;
    end
  end
endmodule
