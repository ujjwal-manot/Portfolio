// Tiny Tapeout IHP shuttle top wrapper (4x4 array) around projects/tensor_core/design/tensor_core.sv using a byte-serial host interface over ui_in/uo_out/uio.
module tt_um_edgesense_tensor (
  input  logic [7:0] ui_in,
  output logic [7:0] uo_out,
  input  logic [7:0] uio_in,
  output logic [7:0] uio_out,
  output logic [7:0] uio_oe,
  input  logic       ena,
  input  logic       clk,
  input  logic       rst_n
);
  logic        we, start, busy;
  logic [2:0]  sel;
  logic [1:0]  fmt, byte_idx;
  logic        mx;
  logic [15:0] addr;
  logic [31:0] wdata, rdata;
  logic        prev_load, prev_start;

  assign sel   = uio_in[2:0];
  assign fmt   = uio_in[4:3];
  assign mx    = uio_in[5];
  assign uio_oe  = 8'h01;
  assign uio_out = {7'b0, busy};

  always_comb begin
    case (byte_idx)
      2'd0:    uo_out = rdata[7:0];
      2'd1:    uo_out = rdata[15:8];
      2'd2:    uo_out = rdata[23:16];
      default: uo_out = rdata[31:24];
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      we         <= 1'b0;
      start      <= 1'b0;
      addr       <= 16'd0;
      byte_idx   <= 2'd0;
      wdata      <= 32'd0;
      prev_load  <= 1'b0;
      prev_start <= 1'b0;
    end else if (ena) begin
      prev_load  <= uio_in[6];
      prev_start <= uio_in[7];
      we         <= 1'b0;
      start      <= 1'b0;
      if (uio_in[6] && !prev_load && !busy) begin
        wdata <= {ui_in, wdata[31:8]};
        if (byte_idx == 2'd3) begin
          we       <= 1'b1;
          byte_idx <= 2'd0;
          addr     <= addr + 16'd1;
        end else begin
          byte_idx <= byte_idx + 2'd1;
        end
      end else if (uio_in[7] && !prev_start && !busy) begin
        start <= 1'b1;
        addr  <= 16'd0;
      end
    end
  end

  tensor_core #(.N(4), .WS(0), .MAXM(8), .MAXK(16), .MAXN(8)) core4x4 (
    .clk(clk), .rst_n(rst_n),
    .we(we), .sel(sel), .addr(addr), .wdata(wdata), .rdata(rdata),
    .start(start), .fmt(fmt), .mx(mx),
    .m(10'd4), .k(10'd8), .n(10'd4), .busy(busy)
  );
endmodule
