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
  logic        we, start, busy, mx;
  logic [2:0]  sel, prev_sel;
  logic [1:0]  fmt, byte_idx;
  logic [15:0] addr;
  logic [31:0] wdata, rdata;
  logic        prev_load, prev_start;

  assign sel     = uio_in[2:0];
  assign fmt     = uio_in[4:3];
  assign uio_oe  = 8'h80;
  assign uio_out = {busy, 7'b0};

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
      mx         <= 1'b0;
      addr       <= 16'd0;
      byte_idx   <= 2'd0;
      wdata      <= 32'd0;
      prev_sel   <= 3'd0;
      prev_load  <= 1'b0;
      prev_start <= 1'b0;
    end else if (ena) begin
      prev_sel   <= sel;
      prev_load  <= uio_in[5];
      prev_start <= uio_in[6];
      we         <= 1'b0;
      start      <= 1'b0;
      if (we) begin
        addr <= addr + 16'd1;
      end
      if (sel != prev_sel) begin
        addr     <= 16'd0;
        byte_idx <= 2'd0;
      end else if (uio_in[5] && !prev_load && !busy) begin
        if (sel == 3'd7) begin
          if (byte_idx == 2'd3) begin
            byte_idx <= 2'd0;
            addr     <= addr + 16'd1;
          end else begin
            byte_idx <= byte_idx + 2'd1;
          end
        end else begin
          wdata <= {ui_in, wdata[31:8]};
          if (byte_idx == 2'd3) begin
            we       <= 1'b1;
            byte_idx <= 2'd0;
          end else begin
            byte_idx <= byte_idx + 2'd1;
          end
        end
      end else if (uio_in[6] && !prev_start && !busy) begin
        mx       <= ui_in[0];
        start    <= 1'b1;
        addr     <= 16'd0;
        byte_idx <= 2'd0;
      end
    end
  end

  tensor_core #(.N(4), .WS(0), .MAXM(8), .MAXK(32), .MAXN(8)) core4x4 (
    .clk(clk), .rst_n(rst_n),
    .we(we), .sel(sel), .addr(addr), .wdata(wdata), .rdata(rdata),
    .start(start), .fmt(fmt), .mx(mx),
    .m(10'd4), .k(10'd8), .n(10'd4), .busy(busy)
  );
endmodule
